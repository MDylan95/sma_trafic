"""
Connecteur TraCI pour l'intégration Mesa ↔ SUMO.
Permet de synchroniser la simulation multi-agent Mesa avec la visualisation SUMO-GUI.

Les agents Mesa prennent les décisions (feux, routage), et SUMO gère
le rendu visuel des véhicules en mouvement.
"""
import os
import sys
import subprocess
import time
import random
import math
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger

try:
    import traci
    import sumolib
    SUMO_AVAILABLE = True
except ImportError:
    SUMO_AVAILABLE = False
    logger.warning("⚠️ SUMO (traci/sumolib) non disponible. Installer avec: pip install eclipse-sumo traci sumolib")

try:
    from .real_network_constants import PONT_DE_GAULLE_EDGES, PONT_HKB_EDGES
    USE_REAL_NETWORK = True
except ImportError:
    USE_REAL_NETWORK = False
    PONT_DE_GAULLE_EDGES = []
    PONT_HKB_EDGES = []


class SumoConnector:
    """
    Connecteur entre la simulation Mesa et SUMO-GUI.
    
    Responsabilités:
    - Lancer SUMO-GUI avec le réseau d'Abidjan
    - Synchroniser les véhicules Mesa → SUMO (ajout, suppression, position)
    - Synchroniser les feux de circulation Mesa → SUMO
    - Récupérer les données SUMO → Mesa (positions réelles, vitesses)
    """
    
    def __init__(self, sumocfg_path: str = None, use_gui: bool = True, 
                 port: int = 8813, delay: int = 0, auto_start: bool = True):
        """
        Args:
            sumocfg_path: Chemin vers le fichier .sumocfg
            use_gui: True pour SUMO-GUI (visualisation), False pour SUMO (headless)
            port: Port TraCI
            delay: Délai d'affichage en ms (0 = temps réel rapide, 100 = lent mais visible)
                   OPTIMISATION: Défaut changé de 100 à 0 pour performance maximale
        """
        if not SUMO_AVAILABLE:
            raise RuntimeError("SUMO n'est pas installé. Exécutez: pip install eclipse-sumo traci sumolib")
        
        if sumocfg_path is None:
            sumocfg_path = os.path.join(os.path.dirname(__file__), "abidjan_real.sumocfg")
        
        self.sumocfg_path = os.path.abspath(sumocfg_path)
        self.use_gui = use_gui
        self.port = port
        self.delay = delay
        self.auto_start = auto_start
        self.connected = False
        
        # Mapping Mesa vehicle ID → SUMO vehicle ID
        self.mesa_to_sumo_vehicles: Dict[str, str] = {}
        # Mapping Mesa intersection ID → SUMO TLS ID
        self.mesa_to_sumo_tls: Dict[str, str] = {}
        
        # Cache du réseau SUMO
        self._net = None
        self._edge_list: List[str] = []
        self._tls_ids: List[str] = []
        
        # Statistiques
        self.vehicles_added = 0
        self.vehicles_removed = 0
        self.tls_updates = 0
        
        # Cache TLS (initialisé ici pour éviter les hasattr dans sync_traffic_lights_from_mesa)
        self._last_tls_states: Dict[str, str] = {}
        self._tls_link_directions: Dict[str, list] = {}

        # Projection UTM: netOffset et zone (extraits au chargement du réseau)
        self._net_offset_x: float = 0.0
        self._net_offset_y: float = 0.0
        self._utm_zone: int = 30  # Zone UTM par défaut pour Abidjan

        # Cache des shapes d'edges pour recherche spatiale rapide
        # Construit une seule fois au démarrage via _build_edge_shape_cache()
        self._edge_shape_cache: Dict[str, Tuple[float, float]] = {}
        # KD-Tree pour recherche O(log n) au lieu de O(n)
        self._kdtree = None
        self._kdtree_edge_ids: List[str] = []

        # Guard : zones géographiques déjà visualisées ?
        self._zones_visualized: bool = False

        # État du blocage incident (maintenu à chaque step)
        self._incident_active: bool = False
        self._blocked_bridge_edges: List[str] = []
        self._bridge_default_speed: float = 13.89
        self._od_pairs_backup: List[Tuple[str, str, List[str]]] = []  # Sauvegarde avant incident
    
    def start(self):
        """Lance SUMO-GUI et établit la connexion TraCI"""
        if not os.path.exists(self.sumocfg_path):
            raise FileNotFoundError(f"Fichier SUMO non trouvé: {self.sumocfg_path}")
        
        sumo_binary = "sumo-gui" if self.use_gui else "sumo"
        
        sumo_cmd = [
            sumo_binary,
            "-c", self.sumocfg_path,
            "--quit-on-end", "true",
            "--delay", str(self.delay),
            "--step-length", "1.0",
            "--time-to-teleport", "-1",
        ]
        
        # Options spécifiques à SUMO-GUI pour améliorer la visualisation
        if self.use_gui:
            sumo_cmd.extend([
                "--gui-settings-file", os.path.join(os.path.dirname(self.sumocfg_path), "gui_settings.xml"),
            ])
        
        if self.auto_start:
            sumo_cmd.append("--start")
        
        logger.info(f"🚀 Lancement de {sumo_binary}...")
        logger.info(f"   Config: {self.sumocfg_path}")
        
        try:
            traci.start(sumo_cmd, port=self.port)
            self.connected = True
            
            # Extraire le netOffset pour la conversion GPS → coordonnées SUMO (lecture XML légère)
            net_file = self.sumocfg_path.replace(".sumocfg", ".net.xml")
            if os.path.exists(net_file):
                self._extract_net_offset(net_file)
            # Note: sumolib.net.readNet supprimé (415 Mo inutile — remplacé par TraCI)
            
            # Récupérer les arêtes et feux
            self._edge_list = traci.edge.getIDList()
            self._tls_ids = traci.trafficlight.getIDList()
            
            # Filtrer les arêtes normales (exclure les internes ":" )
            self._normal_edges = [e for e in self._edge_list if not e.startswith(":")]
            self._source_edges = [e for e in self._normal_edges if "src_" in e]
            
            # Construire le cache spatial des edges (pour find_edge_near_coords)
            self._build_edge_shape_cache()

            # Pré-calculer des paires origine/destination valides
            self._valid_od_pairs = []
            self._precompute_valid_routes()
            
            # Construire le mapping intersections
            self._build_tls_mapping()
            
            # Configurer les noms des routes
            self.setup_road_names()
            
            self._gui_configured = False  # Sera configuré au premier step
            
            logger.info(f"✅ SUMO connecté (port {self.port})")
            logger.info(f"   Arêtes: {len(self._normal_edges)}, Feux: {len(self._tls_ids)}")
            logger.info(f"   Paires O/D valides pré-calculées: {len(self._valid_od_pairs)}")
            
        except Exception as e:
            logger.error(f"❌ Impossible de lancer SUMO: {e}")
            self.connected = False
            raise
    
    def _build_tls_mapping(self):
        """
        Construit le mapping entre intersections Mesa et feux SUMO par position géographique.
        Pour chaque TLS SUMO, on trouve l'intersection Mesa dont la position normalisée
        est la plus proche. Cela évite les erreurs dues à un ordre d'index non garanti.
        """
        if True:
            # Fallback par index si le réseau n'est pas chargé
            for i, tls_id in enumerate(self._tls_ids):
                mesa_id = f"intersection_{i}"
                self.mesa_to_sumo_tls[mesa_id] = tls_id
            return

        # Récupérer les positions des TLS depuis le réseau SUMO
        tls_positions = {}
        for tls_id in self._tls_ids:
            try:
                pos = traci.junction.getPosition(tls_id)  # (x, y) en mètres SUMO
                tls_positions[tls_id] = pos
            except Exception:
                pass

        if not tls_positions:
            # Fallback par index
            for i, tls_id in enumerate(self._tls_ids):
                mesa_id = f"intersection_{i}"
                self.mesa_to_sumo_tls[mesa_id] = tls_id
            return

        # Déterminer les bornes du réseau SUMO pour normaliser
        all_x = [p[0] for p in tls_positions.values()]
        all_y = [p[1] for p in tls_positions.values()]
        sumo_min_x, sumo_max_x = min(all_x), max(all_x)
        sumo_min_y, sumo_max_y = min(all_y), max(all_y)
        sumo_range_x = max(sumo_max_x - sumo_min_x, 1.0)
        sumo_range_y = max(sumo_max_y - sumo_min_y, 1.0)

        # Les intersections Mesa ont des positions dans [0, width] x [0, height]
        # On normalise les deux espaces pour les comparer
        # (importé ici pour éviter la dépendance circulaire au niveau module)
        from agents.intersection_agent import IntersectionAgent as _IA

        # Récupérer les intersections Mesa depuis le modèle
        mesa_intersections = []
        try:
            for agent in self._model_ref.schedule.agents if hasattr(self, '_model_ref') else []:
                if isinstance(agent, _IA):
                    mesa_intersections.append(agent)
        except Exception:
            pass

        if not mesa_intersections:
            # Fallback par index si pas de référence au modèle
            for i, tls_id in enumerate(self._tls_ids):
                mesa_id = f"intersection_{i}"
                self.mesa_to_sumo_tls[mesa_id] = tls_id
            return

        mesa_positions = {a.unique_id: a.position for a in mesa_intersections}
        mesa_x_vals = [p[0] for p in mesa_positions.values()]
        mesa_y_vals = [p[1] for p in mesa_positions.values()]
        mesa_min_x, mesa_max_x = min(mesa_x_vals), max(mesa_x_vals)
        mesa_min_y, mesa_max_y = min(mesa_y_vals), max(mesa_y_vals)
        mesa_range_x = max(mesa_max_x - mesa_min_x, 1.0)
        mesa_range_y = max(mesa_max_y - mesa_min_y, 1.0)

        import math
        for tls_id, (sx, sy) in tls_positions.items():
            # Normaliser la position SUMO
            nx_sumo = (sx - sumo_min_x) / sumo_range_x
            ny_sumo = (sy - sumo_min_y) / sumo_range_y

            # Trouver l'intersection Mesa la plus proche en espace normalisé
            best_id = None
            best_dist = float('inf')
            for mesa_id, (mx, my) in mesa_positions.items():
                nx_mesa = (mx - mesa_min_x) / mesa_range_x
                ny_mesa = (my - mesa_min_y) / mesa_range_y
                dist = math.sqrt((nx_sumo - nx_mesa) ** 2 + (ny_sumo - ny_mesa) ** 2)
                if dist < best_dist:
                    best_dist = dist
                    best_id = mesa_id

            if best_id is not None:
                self.mesa_to_sumo_tls[best_id] = tls_id

        logger.info(f"🗺️  Mapping TLS par position: {len(self.mesa_to_sumo_tls)} intersections mappées")
    
    def _configure_gui_traffic_lights(self):
        """
        Configure automatiquement l'affichage des feux de circulation dans SUMO-GUI.
        Active le schéma 'real world' via TraCI et centre la vue.
        """
        # SUMO-GUI expose toujours la vue principale sous l'ID "View #0"
        view_id = "View #0"
        try:
            # Forcer le schéma "real world" défini dans gui_settings.xml
            traci.gui.setSchema(view_id, "real world")

            # Centrer sur le réseau — getBBoxXY() retourne ((xmin,ymin),(xmax,ymax))
            try:
                bounds = traci.simulation.getNetBoundary()  # ((xmin,ymin),(xmax,ymax))
                center_x = (bounds[0][0] + bounds[1][0]) / 2.0
                center_y = (bounds[0][1] + bounds[1][1]) / 2.0
                traci.gui.setOffset(view_id, center_x, center_y)
            except Exception:
                pass

            # Zoom suffisant pour voir les link decals (feux)
            traci.gui.setZoom(view_id, 2000)

            logger.info(f"🚦 GUI configurée: schéma='real world', zoom=2000, vue='{view_id}'")

        except Exception as e:
            import traceback
            logger.warning(f"⚠️ Impossible de configurer l'affichage GUI des feux: {e}\n{traceback.format_exc()}")
    
    def _precompute_valid_routes(self):
        """
        Pré-calcule des paires origine/destination avec routes valides.
        Cache disque : 1ère exécution ~90s, suivantes ~0.1s.
        """
        import pickle
        od_cache_file = os.path.join(os.path.dirname(self.sumocfg_path), "od_pairs_cache.pkl")

        # --- Charger depuis le cache disque ---
        if os.path.exists(od_cache_file):
            try:
                with open(od_cache_file, "rb") as f:
                    self._valid_od_pairs = pickle.load(f)
                logger.info(f"   ✅ {len(self._valid_od_pairs)} paires O/D chargées depuis cache disque")
                return
            except Exception as e:
                logger.warning(f"⚠️ Cache O/D corrompu, reconstruction... ({e})")

        # --- Construire depuis TraCI ---
        inbound_edges = [e for e in self._source_edges if e.startswith("e_src_") and "_to_n" in e]
        outbound_edges = [e for e in self._source_edges if e.startswith("e_n") and "_to_src_" in e]

        if not inbound_edges or not outbound_edges:
            if len(self._normal_edges) > 100:
                sample_size = min(50, len(self._normal_edges) // 4)
                all_edges_sample = random.sample(self._normal_edges, min(sample_size * 2, len(self._normal_edges)))
                inbound_edges = all_edges_sample[:sample_size]
                outbound_edges = all_edges_sample[sample_size:sample_size*2]
                logger.info(f"🗺️  Réseau OSM détecté : échantillonnage de {sample_size} origines et {sample_size} destinations")
            else:
                inbound_edges = self._normal_edges[:len(self._normal_edges)//2]
                outbound_edges = self._normal_edges[len(self._normal_edges)//2:]

        tested = 0
        valid_count = 0
        for orig in inbound_edges:
            for dest in outbound_edges:
                if orig == dest:
                    continue
                try:
                    route_result = traci.simulation.findRoute(orig, dest)
                    if route_result and route_result.edges and len(route_result.edges) >= 2:
                        self._valid_od_pairs.append((orig, dest, list(route_result.edges)))
                        valid_count += 1
                except Exception:
                    pass
                tested += 1
                if valid_count >= 200:
                    break
            if valid_count >= 200:
                break

        logger.info(f"   ✅ {valid_count} paires O/D valides trouvées (testé {tested} combinaisons)")

        # Sauvegarder sur disque
        try:
            with open(od_cache_file, "wb") as f:
                pickle.dump(self._valid_od_pairs, f)
            logger.info(f"   💾 Cache O/D sauvegardé : {od_cache_file}")
        except Exception as e:
            logger.warning(f"⚠️ Impossible de sauvegarder le cache O/D: {e}")
    
    def step(self):
        """Avance la simulation SUMO d'un pas"""
        if not self.connected:
            return
        try:
            traci.simulationStep()
            # Configurer la GUI au premier pas (traci.gui disponible seulement après simulationStep)
            if not self._gui_configured and self.use_gui:
                self._configure_gui_traffic_lights()
                self._gui_configured = True
        except traci.exceptions.FatalTraCIError:
            logger.warning("⚠️ Connexion SUMO perdue")
            self.connected = False
    
    # ============ CONVERSION GPS → SUMO ============

    def _extract_net_offset(self, net_file: str):
        """Extrait netOffset et projParameter du fichier .net.xml."""
        import xml.etree.ElementTree as ET
        try:
            tree = ET.parse(net_file)
            for loc in tree.getroot().findall('.//location'):
                offset_str = loc.get('netOffset', '0.0,0.0')
                parts = offset_str.split(',')
                self._net_offset_x = float(parts[0])
                self._net_offset_y = float(parts[1])
                proj = loc.get('projParameter', '')
                # Extraire la zone UTM si disponible
                if '+zone=' in proj:
                    zone_str = proj.split('+zone=')[1].split()[0]
                    self._utm_zone = int(zone_str)
                logger.info(
                    f"🗺️  netOffset=({self._net_offset_x:.2f}, {self._net_offset_y:.2f}), UTM zone={self._utm_zone}"
                )
        except Exception as e:
            logger.warning(f"⚠️ Impossible d'extraire netOffset: {e}")

    def _lonlat_to_xy(self, lon: float, lat: float) -> Tuple[float, float]:
        """Convertit des coordonnées GPS (lon, lat) en coordonnées SUMO (x, y) via projection UTM."""
        a = 6378137.0  # WGS84 semi-major axis
        f = 1 / 298.257223563
        e2 = 2 * f - f * f
        lon0 = (self._utm_zone - 1) * 6 - 180 + 3  # méridien central de la zone UTM

        lat_rad = math.radians(lat)
        lon_rad = math.radians(lon)
        lon0_rad = math.radians(lon0)

        N = a / math.sqrt(1 - e2 * math.sin(lat_rad) ** 2)
        T = math.tan(lat_rad) ** 2
        C = (e2 / (1 - e2)) * math.cos(lat_rad) ** 2
        A = (lon_rad - lon0_rad) * math.cos(lat_rad)

        M = a * (
            (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256) * lat_rad
            - (3 * e2 / 8 + 3 * e2 ** 2 / 32 + 45 * e2 ** 3 / 1024) * math.sin(2 * lat_rad)
            + (15 * e2 ** 2 / 256 + 45 * e2 ** 3 / 1024) * math.sin(4 * lat_rad)
            - (35 * e2 ** 3 / 3072) * math.sin(6 * lat_rad)
        )

        k0 = 0.9996
        ep2 = e2 / (1 - e2)
        x_utm = k0 * N * (
            A + (1 - T + C) * A ** 3 / 6
            + (5 - 18 * T + T ** 2 + 72 * C - 58 * ep2) * A ** 5 / 120
        ) + 500000
        y_utm = k0 * (
            M + N * math.tan(lat_rad) * (
                A ** 2 / 2
                + (5 - T + 9 * C + 4 * C ** 2) * A ** 4 / 24
                + (61 - 58 * T + T ** 2 + 600 * C - 330 * ep2) * A ** 6 / 720
            )
        )

        return x_utm + self._net_offset_x, y_utm + self._net_offset_y

    # ============ GESTION DES VÉHICULES ============
    
    def find_edge_near_coords(self, lon: float, lat: float, radius: float = 500.0) -> Optional[str]:
        """Trouve l'edge SUMO le plus proche d'une coordonnée GPS (lon, lat).

        Stratégie en 3 niveaux :
        1. traci.simulation.convertGeo → XY, puis recherche manuelle parmi les edges du réseau
        2. Projection UTM manuelle (_lonlat_to_xy) + recherche manuelle (fallback)
        3. sumolib.getNeighboringEdges (ancien code, gardé en dernier recours)
        """
        if not self.connected:
            return None

        # --- Niveau 1 : conversion via TraCI (la plus fiable) ---
        try:
            x, y = traci.simulation.convertGeo(lon, lat, fromGeo=True)
            edge_id = self._find_nearest_edge_xy(x, y, radius)
            if edge_id:
                logger.debug(
                    f"Edge trouvé via TraCI convertGeo pour ({lon:.4f}, {lat:.4f}) → edge {edge_id}"
                )
                return edge_id
        except Exception as exc:
            logger.debug(f"Niveau 1 (TraCI convertGeo) échoué pour ({lon}, {lat}): {exc}")

        # --- Niveau 2 : KD-Tree sans limite de rayon (edge le plus proche absolu) ---
        try:
            x, y = traci.simulation.convertGeo(lon, lat, fromGeo=True)
            edge_id = self._find_nearest_edge_xy(x, y, radius=float('inf'))
            if edge_id:
                logger.debug(
                    f"Edge trouvé via KD-Tree sans limite pour ({lon:.4f}, {lat:.4f}) → edge {edge_id}"
                )
                return edge_id
        except Exception as exc:
            logger.debug(f"Niveau 2 (KD-Tree sans limite) échoué pour ({lon}, {lat}): {exc}")

        logger.debug(f"Aucun edge trouvé près de ({lon:.4f}, {lat:.4f})")
        return None

    def _build_edge_shape_cache(self):
        """Construit un cache des midpoints d'edges + KD-Tree pour recherche spatiale O(log n).

        1ère exécution : interroge TraCI (~38s) puis sauvegarde sur disque.
        Exécutions suivantes : charge le cache disque (~1s).
        """
        import pickle
        from scipy.spatial import cKDTree

        cache_file = os.path.join(os.path.dirname(self.sumocfg_path), "edge_kdtree_cache.pkl")

        # --- Essayer de charger le cache disque ---
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "rb") as f:
                    cached = pickle.load(f)
                self._edge_shape_cache = cached["cache"]
                coords_arr = cached["coords"]
                self._kdtree_edge_ids = cached["ids"]
                self._kdtree = cKDTree(coords_arr)
                logger.info(f"🗺️  Cache spatial chargé depuis disque : {len(self._kdtree_edge_ids)} edges, KD-Tree prêt")
                return
            except Exception as e:
                logger.warning(f"⚠️ Cache disque corrompu, reconstruction... ({e})")

        # --- Construire depuis TraCI ---
        logger.info("🗺️  Construction du cache spatial des edges (1ère fois, ~30s)...")
        count = 0
        errors = 0
        coords_list = []
        ids_list = []
        for edge_id in self._normal_edges:
            try:
                lane_id = f"{edge_id}_0"
                shape = traci.lane.getShape(lane_id)
                if shape:
                    mx = sum(p[0] for p in shape) / len(shape)
                    my = sum(p[1] for p in shape) / len(shape)
                    self._edge_shape_cache[edge_id] = (mx, my)
                    coords_list.append((mx, my))
                    ids_list.append(edge_id)
                    count += 1
                    continue
            except Exception:
                pass
            try:
                shape = traci.edge.getShape(edge_id)
                if shape:
                    mx = sum(p[0] for p in shape) / len(shape)
                    my = sum(p[1] for p in shape) / len(shape)
                    self._edge_shape_cache[edge_id] = (mx, my)
                    coords_list.append((mx, my))
                    ids_list.append(edge_id)
                    count += 1
                    continue
            except Exception:
                pass
            errors += 1

        if coords_list:
            coords_arr = np.array(coords_list)
            self._kdtree = cKDTree(coords_arr)
            self._kdtree_edge_ids = ids_list
            # Sauvegarder sur disque pour les prochaines exécutions
            try:
                with open(cache_file, "wb") as f:
                    pickle.dump({"cache": self._edge_shape_cache, "coords": coords_arr, "ids": ids_list}, f)
                logger.info(f"   💾 Cache sauvegardé : {cache_file}")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de sauvegarder le cache disque: {e}")

        logger.info(f"   ✅ Cache spatial: {count} edges indexés ({errors} erreurs), KD-Tree construit")

    def _find_nearest_edge_xy(self, x: float, y: float, radius: float = 500.0) -> Optional[str]:
        """Trouve l'edge normal le plus proche des coordonnées SUMO (x, y) via KD-Tree.

        Complexité O(log n) au lieu de O(n) grâce au KD-Tree.
        """
        if self._kdtree is not None:
            dist, idx = self._kdtree.query([x, y])
            if dist <= radius:
                return self._kdtree_edge_ids[idx]

        # Fallback linéaire si KD-Tree non disponible
        best_edge = None
        best_dist_sq = float('inf')
        for edge_id, (mx, my) in self._edge_shape_cache.items():
            dist_sq = (x - mx) ** 2 + (y - my) ** 2
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_edge = edge_id
        if best_edge and best_dist_sq <= radius * radius:
            return best_edge
        return None
    
    def add_vehicle(self, mesa_vehicle_id: str, vehicle_type: str = "standard",
                    origin_edge: str = None, dest_edge: str = None,
                    origin_coords: Tuple[float, float] = None, dest_coords: Tuple[float, float] = None):
        """
        Ajoute un véhicule dans SUMO correspondant à un VehicleAgent Mesa.
        
        Args:
            mesa_vehicle_id: ID du véhicule Mesa
            vehicle_type: Type de véhicule SUMO
            origin_edge: Edge de départ (optionnel si origin_coords fourni)
            dest_edge: Edge d'arrivée (optionnel si dest_coords fourni)
            origin_coords: Coordonnées GPS (lon, lat) de départ
            dest_coords: Coordonnées GPS (lon, lat) d'arrivée
        """
        if not self.connected:
            return False
        
        sumo_veh_id = f"mesa_{mesa_vehicle_id}"
        
        # Éviter les doublons
        if mesa_vehicle_id in self.mesa_to_sumo_vehicles:
            return True
        
        route_id = f"route_{sumo_veh_id}"
        
        try:
            use_fallback_route = False
            # Si coordonnées GPS fournies, trouver les edges correspondants
            if origin_coords is not None and origin_edge is None:
                lon, lat = origin_coords
                origin_edge = self.find_edge_near_coords(lon, lat)
                if origin_edge is None:
                    logger.debug(f"Aucun edge trouvé près de ({lon}, {lat}) — fallback route")
                    use_fallback_route = True
            
            if dest_coords is not None and dest_edge is None:
                lon, lat = dest_coords
                dest_edge = self.find_edge_near_coords(lon, lat)
                if dest_edge is None:
                    logger.debug(f"Aucun edge trouvé près de ({lon}, {lat}) — fallback route")
                    use_fallback_route = True
            
            # Méthode 1 : Utiliser les edges fournis ou trouvés
            if not use_fallback_route and origin_edge and dest_edge:
                # Utiliser traci.simulation.findRoute (C++ natif, beaucoup plus rapide)
                try:
                    route_result = traci.simulation.findRoute(origin_edge, dest_edge)
                    if route_result and route_result.edges and len(route_result.edges) >= 2:
                        route_edges = list(route_result.edges)
                        traci.route.add(route_id, route_edges)
                        traci.vehicle.add(sumo_veh_id, route_id, typeID=vehicle_type)
                        self.mesa_to_sumo_vehicles[mesa_vehicle_id] = sumo_veh_id
                        self.vehicles_added += 1
                        logger.debug(
                            f"➕ Véhicule {sumo_veh_id} ajouté avec edges GPS {origin_edge} → {dest_edge} (type={vehicle_type})"
                        )
                        return True
                except Exception:
                    pass
            
            # Méthode 2 : Utiliser une paire O/D pré-calculée (fallback)
            if self._valid_od_pairs:
                od = random.choice(self._valid_od_pairs)
                origin, dest, edges = od
                traci.route.add(route_id, edges)
                traci.vehicle.add(sumo_veh_id, route_id, typeID=vehicle_type)
                self.mesa_to_sumo_vehicles[mesa_vehicle_id] = sumo_veh_id
                self.vehicles_added += 1
                logger.debug(
                    f"➕ Véhicule {sumo_veh_id} ajouté via paire O/D pré-calculée {origin} → {dest} (type={vehicle_type})"
                )
                return True
            
            # Méthode 3 : Trouver une route aléatoire
            if origin_edge is None:
                origin_edge = random.choice(self._source_edges) if self._source_edges else random.choice(self._normal_edges)
            if dest_edge is None:
                candidates = [e for e in self._source_edges if e != origin_edge]
                if not candidates:
                    candidates = [e for e in self._normal_edges if e != origin_edge]
                dest_edge = random.choice(candidates)
            
            try:
                route_result = traci.simulation.findRoute(origin_edge, dest_edge)
                if route_result and route_result.edges and len(route_result.edges) >= 2:
                    route_edges = list(route_result.edges)
                    traci.route.add(route_id, route_edges)
                    traci.vehicle.add(sumo_veh_id, route_id, typeID=vehicle_type)
                    self.mesa_to_sumo_vehicles[mesa_vehicle_id] = sumo_veh_id
                    self.vehicles_added += 1
                    logger.debug(
                        f"➕ Véhicule {sumo_veh_id} ajouté via route aléatoire {origin_edge} → {dest_edge} (type={vehicle_type})"
                    )
                    return True
            except Exception:
                pass
            
            return False
            
        except traci.exceptions.TraCIException as e:
            logger.debug(f"❌ Impossible d'ajouter {sumo_veh_id}: {e}")
            return False
    
    def remove_vehicle(self, mesa_vehicle_id: str):
        """Supprime un véhicule de SUMO (quand il arrive à destination dans Mesa)"""
        if not self.connected:
            return
        
        sumo_veh_id = self.mesa_to_sumo_vehicles.get(mesa_vehicle_id)
        if sumo_veh_id is None:
            return
        
        try:
            if sumo_veh_id in traci.vehicle.getIDList():
                traci.vehicle.remove(sumo_veh_id)
            del self.mesa_to_sumo_vehicles[mesa_vehicle_id]
            self.vehicles_removed += 1
        except traci.exceptions.TraCIException:
            pass
    
    def update_vehicle_color(self, mesa_vehicle_id: str, color: Tuple[int, int, int, int]):
        """Met à jour la couleur d'un véhicule (ex: rouge pour congestion)"""
        if not self.connected:
            return
        
        sumo_veh_id = self.mesa_to_sumo_vehicles.get(mesa_vehicle_id)
        if sumo_veh_id is None:
            return
        
        try:
            if sumo_veh_id in traci.vehicle.getIDList():
                traci.vehicle.setColor(sumo_veh_id, color)
        except traci.exceptions.TraCIException:
            pass
    
    def get_vehicle_data(self, mesa_vehicle_id: str) -> Optional[Dict]:
        """Récupère les données d'un véhicule depuis SUMO"""
        if not self.connected:
            return None
        
        sumo_veh_id = self.mesa_to_sumo_vehicles.get(mesa_vehicle_id)
        if sumo_veh_id is None:
            return None
        
        try:
            if sumo_veh_id in traci.vehicle.getIDList():
                return {
                    'position': traci.vehicle.getPosition(sumo_veh_id),
                    'speed': traci.vehicle.getSpeed(sumo_veh_id),
                    'edge': traci.vehicle.getRoadID(sumo_veh_id),
                    'route': traci.vehicle.getRoute(sumo_veh_id),
                    'waiting_time': traci.vehicle.getWaitingTime(sumo_veh_id),
                }
        except traci.exceptions.TraCIException:
            pass
        return None
    
    # ============ GESTION DES FEUX ============
    
    def update_traffic_light(self, mesa_intersection_id: str, phase_state: str):
        """
        Met à jour l'état d'un feu de circulation dans SUMO.
        
        Args:
            mesa_intersection_id: ID de l'intersection Mesa
            phase_state: État des feux au format SUMO (ex: "GGrrGGrr")
                G = vert, g = vert priorité, r = rouge, y = jaune
        """
        if not self.connected:
            return
        
        tls_id = self.mesa_to_sumo_tls.get(mesa_intersection_id)
        if tls_id is None:
            return
        
        try:
            traci.trafficlight.setRedYellowGreenState(tls_id, phase_state)
            self.tls_updates += 1
        except traci.exceptions.TraCIException as e:
            logger.debug(f"Erreur mise à jour feu {tls_id}: {e}")
    
    def _is_ns_edge(self, edge_id: str) -> bool:
        """
        Détermine si une arête est dans la direction Nord-Sud.
        Convention du réseau: e_nR1_C_to_nR2_C → la rangée change = N/S
                              e_nR_C1_to_nR_C2 → la colonne change = E/O
        """
        import re
        # Pattern: e_nROW_COL_to_nROW_COL
        match = re.match(r'e_n(\d+)_(\d+)_to_n(\d+)_(\d+)', edge_id)
        if match:
            r1, c1, r2, c2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            return r1 != r2  # Rangée change = direction N/S
        # Arêtes source (src_south/north = N/S, src_east/west = E/O)
        if 'south' in edge_id or 'north' in edge_id:
            return True
        return False

    def sync_traffic_lights_from_mesa(self, intersections):
        """
        Synchronise tous les feux de circulation Mesa → SUMO.
        
        Ne met à jour SUMO que lorsque l'état Mesa change réellement
        pour éviter les clignotements.
        """
        if not self.connected:
            return
        
        from agents.intersection_agent import Direction, TrafficLightState
        
        # Pré-calculer le mapping liens→directions (une seule fois, si pas encore fait)
        if not self._tls_link_directions:
            for tls_id in self.mesa_to_sumo_tls.values():
                try:
                    links = traci.trafficlight.getControlledLinks(tls_id)
                    directions = []
                    for link in links:
                        if link and len(link) > 0:
                            in_lane = link[0][0] if link[0] else ""
                            edge_name = in_lane.rsplit('_', 1)[0] if '_' in in_lane else in_lane
                            directions.append('NS' if self._is_ns_edge(edge_name) else 'EW')
                        else:
                            directions.append('EW')
                    self._tls_link_directions[tls_id] = directions
                except traci.exceptions.TraCIException:
                    pass
            logger.info(f"🔍 Mapping TLS pré-calculé pour {len(self._tls_link_directions)} feux")
        
        # Cache des états de phase par TLS (initialisé une seule fois)
        if not hasattr(self, '_tls_phase_states'):
            self._tls_phase_states = {}  # {tls_id: {0: "GGGGrrr", 2: "rrrrGGG"}}
        
        for intersection in intersections:
            tls_id = self.mesa_to_sumo_tls.get(intersection.unique_id)
            if tls_id is None:
                continue
            
            try:
                # Déterminer la phase actuelle Mesa : NS ou EW en vert ?
                phase = intersection._get_current_phase()  # retourne 'NS' ou 'EW'
                target_phase_idx = 0 if phase == 'NS' else 2
                
                # Ne mettre à jour que si la phase a changé
                last_phase = self._last_tls_states.get(tls_id)
                if last_phase == target_phase_idx:
                    continue
                
                # Charger le cache des états de phase pour ce TLS si nécessaire
                if tls_id not in self._tls_phase_states:
                    logics = traci.trafficlight.getAllProgramLogics(tls_id)
                    if logics and logics[0].phases:
                        phases = logics[0].phases
                        n = len(phases)
                        # Phase principale (index 0) et phase secondaire (index 2 si >= 3 phases)
                        self._tls_phase_states[tls_id] = {
                            0: phases[0].state,
                            2: phases[min(2, n - 1)].state
                        }
                    else:
                        # Aucun programme disponible, ignorer ce TLS
                        self._tls_phase_states[tls_id] = {}
                
                cached = self._tls_phase_states.get(tls_id, {})
                if target_phase_idx not in cached:
                    continue
                
                # Appliquer l'état exact de la phase via setRedYellowGreenState
                # (plus fiable que setPhase qui peut être écrasé par le timer SUMO)
                state_str = cached[target_phase_idx]
                traci.trafficlight.setRedYellowGreenState(tls_id, state_str)
                self._last_tls_states[tls_id] = target_phase_idx
                self.tls_updates += 1
                
            except traci.exceptions.TraCIException:
                pass
    
    # ============ VISUALISATION DES ZONES GÉOGRAPHIQUES ============
    
    def visualize_geographic_zones(self):
        """
        Visualise les zones géographiques (Yopougon, Abobo, Plateau) dans SUMO-GUI
        avec des polygones colorés pour vérifier le flux du scénario rush_hour.
        """
        if not self.connected or not self.use_gui:
            logger.debug("Zones géo: SUMO non connecté ou GUI désactivée")
            return

        if self._zones_visualized:
            logger.debug("Zones géographiques déjà visualisées, appel ignoré")
            return
        
        try:
            from .real_network_constants import BBOX_YOPOUGON, BBOX_ABOBO, BBOX_PLATEAU
            
            zones = [
                {
                    'name': 'Yopougon',
                    'bbox': BBOX_YOPOUGON,
                    'color': (100, 150, 255, 255),  # Bleu (contour)
                },
                {
                    'name': 'Abobo',
                    'bbox': BBOX_ABOBO,
                    'color': (150, 100, 255, 255),  # Violet (contour)
                },
                {
                    'name': 'Plateau',
                    'bbox': BBOX_PLATEAU,
                    'color': (255, 100, 100, 255),  # Rouge (contour)
                }
            ]
            
            logger.info("🗺️  Tentative de visualisation des zones géographiques...")
            
            for zone in zones:
                bbox = zone['bbox']  # (lon_min, lat_min, lon_max, lat_max)
                
                try:
                    # Convertir les coins GPS en coordonnées SUMO
                    # convertGeo(lon, lat, fromGeo=True) convertit GPS → XY SUMO
                    x1, y1 = traci.simulation.convertGeo(bbox[0], bbox[1], fromGeo=True)  # Sud-Ouest
                    x2, y2 = traci.simulation.convertGeo(bbox[2], bbox[3], fromGeo=True)  # Nord-Est
                    
                    logger.info(f"   Zone {zone['name']}: GPS ({bbox[0]:.4f},{bbox[1]:.4f})-({bbox[2]:.4f},{bbox[3]:.4f}) → SUMO ({x1:.0f},{y1:.0f})-({x2:.0f},{y2:.0f})")
                    
                    # Créer un polygone rectangulaire
                    shape = [
                        (x1, y1),  # Sud-Ouest
                        (x2, y1),  # Sud-Est
                        (x2, y2),  # Nord-Est
                        (x1, y2),  # Nord-Ouest
                    ]
                    
                    poly_id = f"zone_{zone['name'].lower()}"
                    
                    # Ajouter le polygone avec un layer élevé pour être visible
                    traci.polygon.add(
                        polygonID=poly_id,
                        shape=shape,
                        color=zone['color'],
                        fill=False,
                        polygonType="zone",
                        layer=5  # couche basse pour laisser véhicules et routes visibles
                    )
                    
                    # Ajouter un POI (label) au centre
                    center_x = (x1 + x2) / 2
                    center_y = (y1 + y2) / 2
                    poi_id = f"label_{zone['name'].lower()}"
                    
                    traci.poi.add(
                        poiID=poi_id,
                        x=center_x,
                        y=center_y,
                        color=(0, 0, 0, 255),
                        poiType="label"
                    )
                    
                    logger.info(f"   ✅ Zone {zone['name']} ajoutée (polygone + POI)")
                    
                except traci.exceptions.TraCIException as e:
                    logger.warning(f"   ❌ Erreur zone {zone['name']}: {e}")
                    continue
            
            self._zones_visualized = True
            logger.info("🗺️  Zones géographiques visualisées: Yopougon=🟦 Bleu, Abobo=🟪 Violet, Plateau=🟥 Rouge")
            logger.info("   💡 Si vous ne voyez pas les zones, zoomez/dézoomez dans SUMO-GUI ou vérifiez View → Show Polygons")
            
        except ImportError:
            logger.warning("⚠️ Impossible d'importer les constantes géographiques")
        except Exception as e:
            logger.warning(f"⚠️ Erreur visualisation zones géographiques: {e}")
            import traceback
            logger.debug(traceback.format_exc())
    
    # ============ VISUALISATION DES INCIDENTS ============
    
    def highlight_blocked_edges(self, edge_ids: List[str], color: Tuple[int, int, int] = (255, 0, 0)):
        """
        Colore les arêtes bloquées en rouge pour visualiser un incident.
        
        Args:
            edge_ids: Liste des IDs d'arêtes à colorer
            color: Tuple RGB (défaut: rouge pour incident)
        """
        if not self.connected:
            return
        
        try:
            for edge_id in edge_ids:
                if edge_id in self._edge_list:
                    traci.edge.setParameter(edge_id, "color", f"{color[0]},{color[1]},{color[2]}")
        except traci.exceptions.TraCIException:
            pass
    
    def clear_edge_highlighting(self, edge_ids: List[str]):
        """Restaure la couleur par défaut des arêtes"""
        if not self.connected:
            return
        
        try:
            for edge_id in edge_ids:
                if edge_id in self._edge_list:
                    traci.edge.setParameter(edge_id, "color", "")
        except traci.exceptions.TraCIException:
            pass
    
    def highlight_pont_de_gaulle(self, highlight: bool = True):
        """
        Colore le Pont De Gaulle en jaune pour le localiser facilement.
        Le Pont De Gaulle est composé des arêtes verticales (N-S) au centre du réseau.
        """
        if not self.connected:
            return
        
        # Pont De Gaulle = arêtes N-S au centre (colonne 2-3 sur grille 6x6)
        pont_edges = []
        for r in range(5):  # 5 arêtes verticales (0-1, 1-2, 2-3, 3-4, 4-5)
            for c in [2, 3]:  # Colonnes centrales
                edge_id = f"e_n{r}_{c}_to_n{r+1}_{c}"
                if edge_id in self._edge_list:
                    pont_edges.append(edge_id)
                # Arête inverse
                edge_id_rev = f"e_n{r+1}_{c}_to_n{r}_{c}"
                if edge_id_rev in self._edge_list:
                    pont_edges.append(edge_id_rev)
        
        if highlight:
            self.highlight_blocked_edges(pont_edges, color=(255, 255, 0))  # Jaune
        else:
            self.clear_edge_highlighting(pont_edges)
    
    def setup_road_names(self):
        """
        Configure les noms des routes dans SUMO-GUI.
        Affiche les noms descriptifs pour faciliter l'identification.
        """
        if not self.connected:
            return
        
        try:
            from sumo_integration.road_names import get_road_name
            
            # Ajouter les noms à toutes les arêtes
            for edge_id in self._edge_list:
                road_name = get_road_name(edge_id)
                if road_name and road_name != edge_id:
                    try:
                        traci.edge.setParameter(edge_id, "name", road_name)
                    except traci.exceptions.TraCIException:
                        pass
            
            logger.info(f"✅ Noms de routes configurés pour {len(self._edge_list)} arêtes")
        except Exception as e:
            logger.warning(f"⚠️ Impossible de configurer les noms de routes: {e}")
    
    # ============ SYNCHRONISATION COMPLÈTE ============
    
    def sync_vehicles_from_mesa(self, vehicles):
        """
        Synchronise les véhicules Mesa → SUMO.
        Ajoute les nouveaux, supprime ceux qui sont arrivés.
        """
        if not self.connected:
            return
        
        active_mesa_ids = set()
        
        for vehicle in vehicles:
            if vehicle.active:
                active_mesa_ids.add(vehicle.unique_id)
                
                # Ajouter le véhicule s'il n'existe pas encore dans SUMO
                if vehicle.unique_id not in self.mesa_to_sumo_vehicles:
                    vtype = getattr(vehicle, 'vehicle_type', 'standard')
                    self.add_vehicle(vehicle.unique_id, vehicle_type=vtype)
        
        # Supprimer les véhicules qui ne sont plus actifs dans Mesa
        to_remove = [
            mid for mid in self.mesa_to_sumo_vehicles 
            if mid not in active_mesa_ids
        ]
        for mid in to_remove:
            self.remove_vehicle(mid)
    
    def sync_step(self, model):
        """
        Synchronisation complète pour un pas de simulation.
        Appelé à chaque step du modèle Mesa.
        
        Args:
            model: Instance de TrafficModel
        """
        if not self.connected:
            return
        
        # Stocker la référence au modèle pour le mapping TLS géographique
        self._model_ref = model
        
        # 1. Synchroniser les véhicules Mesa → SUMO
        self.sync_vehicles_from_mesa(model.vehicles)
        
        # 2. Synchroniser les feux Mesa → SUMO
        self.sync_traffic_lights_from_mesa(model.intersections)
        
        # 3. Maintenir le blocage incident si actif
        if self._incident_active and self._blocked_bridge_edges:
            for edge_id in self._blocked_bridge_edges:
                try:
                    if edge_id in self._edge_list:
                        traci.edge.setDisallowed(edge_id, ["passenger", "bus", "emergency", "truck", "motorcycle"])
                        traci.edge.adaptTraveltime(edge_id, 1e9)
                        traci.edge.setEffort(edge_id, 1e9)
                        lane_count = traci.edge.getLaneNumber(edge_id)
                        for lane_idx in range(lane_count):
                            traci.lane.setMaxSpeed(f"{edge_id}_{lane_idx}", 0.0)
                except Exception:
                    pass
            # Re-router les véhicules qui ont encore une route passant par le pont
            try:
                for sumo_veh_id in traci.vehicle.getIDList():
                    try:
                        route_edges = traci.vehicle.getRoute(sumo_veh_id)
                        if any(e in self._blocked_bridge_edges for e in route_edges):
                            traci.vehicle.rerouteTraveltime(sumo_veh_id, currentTravelTimes=True)
                    except Exception:
                        pass
            except Exception:
                pass

        # 4. Avancer SUMO d'un pas
        self.step()
    
    # ============ VISUALISATION INCIDENTS ============

    def highlight_pont_de_gaulle(self, highlight: bool = True,
                                  rows: int = 6, bridge_col: int = 2):
        """
        Visualise l'incident sur le Pont De Gaulle dans SUMO-GUI :
        - Dessine un polygone rouge semi-transparent sur le pont (incident actif)
        - Réduit la vitesse max des lanes à 0 pour bloquer physiquement le trafic
        - Supprime le polygone et restaure la vitesse à la résolution

        Args:
            highlight: True = incident actif, False = incident résolu
            rows: Nombre de rangées du réseau (ignoré si réseau réel OSM)
            bridge_col: Colonne du réseau (ignoré si réseau réel OSM)
        """
        if not self.connected:
            return

        poly_id = "incident_pont_de_gaulle"
        poi_id  = "incident_poi_pont_de_gaulle"

        # Utiliser les vrais edges OSM si disponibles, sinon calculer par grille
        if USE_REAL_NETWORK and PONT_DE_GAULLE_EDGES:
            bridge_edge_ids = PONT_DE_GAULLE_EDGES
            logger.info(f"🌍 Utilisation du réseau réel OSM : {len(bridge_edge_ids)} edges du Pont De Gaulle")
        else:
            # Fallback : réseau grille (ancien comportement)
            spacing = 500.0
            offset = 500.0
            bridge_edge_ids = []
            for r in range(rows - 1):
                bridge_edge_ids.append(f"e_n{r}_{bridge_col}_to_n{r+1}_{bridge_col}")
                bridge_edge_ids.append(f"e_n{r+1}_{bridge_col}_to_n{r}_{bridge_col}")
            logger.info(f"📐 Utilisation du réseau grille : {len(bridge_edge_ids)} edges calculés")

        if highlight:
            # Mémoriser les edges bloqués pour le maintien à chaque step
            self._incident_active = True
            self._blocked_bridge_edges = bridge_edge_ids

            logger.info(f"🚧 Blocage SUMO : {len(bridge_edge_ids)} edges à bloquer")
            print(f"\n🚧 BLOCAGE INCIDENT: {len(bridge_edge_ids)} edges du Pont De Gaulle")

            # --- Étape 1 : Sauvegarder et purger les paires O/D qui passent par le pont ---
            # IMPORTANT: Sauvegarder TOUTES les paires O/D avant de les modifier
            self._od_pairs_backup = list(self._valid_od_pairs)  # Copie complète
            
            before = len(self._valid_od_pairs)
            self._valid_od_pairs = [
                (o, d, edges) for o, d, edges in self._valid_od_pairs
                if not any(e in bridge_edge_ids for e in edges)
            ]
            purged = before - len(self._valid_od_pairs)
            print(f"💾 {before} paires O/D sauvegardées")
            print(f"🗑️ {purged} paires O/D passant par le pont supprimées ({len(self._valid_od_pairs)} restantes)")

            # --- Étape 2 : Bloquer complètement les edges ---
            blocked_count = 0
            for edge_id in bridge_edge_ids:
                try:
                    if edge_id not in self._edge_list:
                        logger.warning(f"⚠️ Edge {edge_id} n'existe pas dans SUMO")
                        continue
                    traci.edge.setDisallowed(edge_id, ["passenger", "bus", "emergency", "truck", "motorcycle"])
                    traci.edge.adaptTraveltime(edge_id, 1e9)
                    traci.edge.setEffort(edge_id, 1e9)
                    lane_count = traci.edge.getLaneNumber(edge_id)
                    for lane_idx in range(lane_count):
                        traci.lane.setMaxSpeed(f"{edge_id}_{lane_idx}", 0.0)
                    blocked_count += 1
                except Exception as e:
                    logger.error(f"❌ Erreur blocage {edge_id}: {e}")
            print(f"✅ {blocked_count}/{len(bridge_edge_ids)} edges bloqués")

            # --- Étape 3 : Gérer les véhicules actifs ---
            removed_on_bridge = 0
            rerouted = 0
            try:
                active_sumo_vehicles = list(traci.vehicle.getIDList())
                for sumo_veh_id in active_sumo_vehicles:
                    try:
                        current_edge = traci.vehicle.getRoadID(sumo_veh_id)
                        route_edges = traci.vehicle.getRoute(sumo_veh_id)
                        if current_edge in bridge_edge_ids:
                            # Véhicule PHYSIQUEMENT sur le pont : le supprimer
                            traci.vehicle.remove(sumo_veh_id)
                            removed_on_bridge += 1
                        elif any(e in bridge_edge_ids for e in route_edges):
                            # Véhicule dont la route passe par le pont : re-router
                            traci.vehicle.rerouteTraveltime(sumo_veh_id, currentTravelTimes=True)
                            rerouted += 1
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"❌ Erreur gestion véhicules: {e}")
            print(f"🚨 {removed_on_bridge} véhicules retirés du pont, 🔄 {rerouted} re-routés\n")

            # --- Dessiner un polygone rouge sur le pont ---
            # Calculer les coordonnées du polygone à partir des edges réels
            try:
                # Récupérer les coordonnées des edges du pont
                all_coords = []
                for edge_id in bridge_edge_ids:
                    if edge_id in self._edge_list:
                        try:
                            shape = traci.edge.getShape(edge_id)
                            all_coords.extend(shape)
                        except Exception:
                            pass
                
                if all_coords:
                    # Calculer la bounding box du pont
                    xs = [c[0] for c in all_coords]
                    ys = [c[1] for c in all_coords]
                    x_min, x_max = min(xs), max(xs)
                    y_min, y_max = min(ys), max(ys)
                    x_center = (x_min + x_max) / 2.0
                    y_center = (y_min + y_max) / 2.0
                    
                    # Créer un polygone englobant avec marge
                    margin = 30.0  # mètres de marge
                    shape = [
                        (x_min - margin, y_min - margin),
                        (x_max + margin, y_min - margin),
                        (x_max + margin, y_max + margin),
                        (x_min - margin, y_max + margin),
                    ]
                    
                    existing_polys = traci.polygon.getIDList()
                    if poly_id not in existing_polys:
                        traci.polygon.add(
                            poly_id,
                            shape,
                            color=(255, 0, 0, 180),   # rouge semi-transparent
                            fill=True,
                            polygonType="incident",
                            layer=10
                        )
                        traci.polygon.setColor(poly_id, (255, 0, 0, 180))
                        logger.info(f"🟥 Polygone rouge créé sur le pont (ID: {poly_id})")
                        print(f"🟥 Polygone rouge créé: {poly_id} (bbox: {x_min:.1f}-{x_max:.1f}, {y_min:.1f}-{y_max:.1f})")
                    
                    # --- Ajouter un POI au centre du pont ---
                    existing_pois = traci.poi.getIDList()
                    if poi_id not in existing_pois:
                        traci.poi.add(
                            poi_id,
                            x_center,
                            y_center,
                            color=(255, 0, 0, 255),
                            poiType="incident",
                            layer=11
                        )
                        logger.info(f"📍 POI incident créé au centre du pont")
                        print(f"📍 POI créé au centre du pont")
            except Exception as e:
                logger.error(f"❌ Erreur création polygone/POI: {e}")
                print(f"❌ ERREUR polygone/POI: {e}")

            logger.warning(
                "🚨 [SUMO-GUI] INCIDENT ACTIF — Pont De Gaulle bloqué "
                "(polygone rouge + vitesse=0 sur les lanes)"
            )

        else:
            # Désactiver le maintien du blocage
            self._incident_active = False
            self._blocked_bridge_edges = []

            logger.info("🔧 RÉSOLUTION INCIDENT : Restauration du Pont De Gaulle")
            print("\n🔧 RÉSOLUTION INCIDENT : Restauration du Pont De Gaulle")

            # --- Restaurer l'accès normal et la vitesse des edges ---
            default_speed = self._bridge_default_speed
            restored_count = 0
            for edge_id in bridge_edge_ids:
                try:
                    traci.edge.setAllowed(edge_id, ["passenger", "bus", "emergency", "truck", "motorcycle"])
                    # Restaurer temps de trajet normal (recalculé par SUMO)
                    traci.edge.adaptTraveltime(edge_id, -1)
                    traci.edge.setEffort(edge_id, -1)
                    lane_count = traci.edge.getLaneNumber(edge_id)
                    for lane_idx in range(lane_count):
                        traci.lane.setMaxSpeed(f"{edge_id}_{lane_idx}", default_speed)
                    restored_count += 1
                except Exception:
                    pass
            print(f"✅ {restored_count}/{len(bridge_edge_ids)} edges restaurés")

            # --- Restaurer les paires O/D sauvegardées ---
            # IMPORTANT : Restaurer EXACTEMENT les paires O/D d'avant l'incident
            # au lieu de recalculer de nouvelles paires aléatoires
            if self._od_pairs_backup:
                self._valid_od_pairs = list(self._od_pairs_backup)  # Restaurer la sauvegarde
                self._od_pairs_backup = []  # Vider la sauvegarde
                print(f"♻️ {len(self._valid_od_pairs)} paires O/D restaurées (état d'avant incident)")
            else:
                # Fallback si pas de sauvegarde : recalculer
                logger.warning("⚠️ Pas de sauvegarde O/D, recalcul nécessaire")
                self._valid_od_pairs.clear()
                self._precompute_valid_routes()
                print(f"🔄 {len(self._valid_od_pairs)} paires O/D recalculées")

            # --- Re-router TOUS les véhicules actifs pour qu'ils utilisent le pont à nouveau ---
            rerouted_count = 0
            try:
                active_sumo_vehicles = list(traci.vehicle.getIDList())
                for sumo_veh_id in active_sumo_vehicles:
                    try:
                        # Re-router le véhicule pour qu'il recalcule son trajet avec le pont restauré
                        traci.vehicle.rerouteTraveltime(sumo_veh_id, currentTravelTimes=True)
                        rerouted_count += 1
                    except Exception:
                        pass
                print(f"🔄 {rerouted_count} véhicules re-routés pour utiliser le pont restauré")
            except Exception as e:
                logger.error(f"❌ Erreur re-routing véhicules: {e}")

            print(f"✅ Incident résolu : {rerouted_count} véhicules continuent leur trajet\n")

            # --- Supprimer le polygone ---
            try:
                existing_polys = traci.polygon.getIDList()
                if poly_id in existing_polys:
                    traci.polygon.remove(poly_id)
            except Exception:
                pass

            # --- Supprimer le POI ---
            try:
                existing_pois = traci.poi.getIDList()
                if poi_id in existing_pois:
                    traci.poi.remove(poi_id)
            except Exception:
                pass

            logger.info(
                "✅ [SUMO-GUI] Incident résolu — Pont De Gaulle restauré "
                "(polygone supprimé, vitesse normale rétablie)"
            )

    # ============ UTILITAIRES ============
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques du connecteur SUMO"""
        stats = {
            'connected': self.connected,
            'vehicles_in_sumo': len(traci.vehicle.getIDList()) if self.connected else 0,
            'vehicles_added_total': self.vehicles_added,
            'vehicles_removed_total': self.vehicles_removed,
            'tls_updates_total': self.tls_updates,
            'mapped_vehicles': len(self.mesa_to_sumo_vehicles),
            'mapped_tls': len(self.mesa_to_sumo_tls),
        }
        
        if self.connected:
            stats['simulation_time'] = traci.simulation.getTime()
        
        return stats
    
    def close(self):
        """Ferme la connexion SUMO"""
        if self.connected:
            try:
                traci.close()
                logger.info("✅ Connexion SUMO fermée")
            except Exception:
                pass
            self.connected = False
    
    def __del__(self):
        self.close()
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
