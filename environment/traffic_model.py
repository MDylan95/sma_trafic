"""
Modèle principal de simulation du système multi-agent de régulation du trafic
Utilise le framework Mesa
"""
import random
from typing import List, Tuple, Dict
import yaml
import numpy as np
from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
from datetime import datetime
from loguru import logger

from agents.vehicle_agent import VehicleAgent
from agents.intersection_agent import IntersectionAgent
from agents.crisis_manager_agent import CrisisManagerAgent
from algorithms.routing import RoadNetwork, AStarRouter, DynamicRouter
from communication.fipa_message import MessageRouter
from utils.database import PostgreSQLDatabase
from scenarios.rush_hour import setup_scenario as setup_rush_hour, run_scenario_step as rush_hour_step
from scenarios.incident import IncidentScenario

# Import optionnel de SUMO
try:
    from sumo_integration.sumo_connector import SumoConnector
    SUMO_AVAILABLE = True
except ImportError:
    SUMO_AVAILABLE = False


class TrafficModel(Model):
    """
    Modèle principal de simulation du trafic
    
    Gère:
    - La création et l'ordonnancement des agents
    - Le réseau routier
    - La collecte de données
    - Le routage des messages
    """
    
    def __init__(self, config_path: str = "config.yaml", use_sumo: bool = False, sumo_gui: bool = True,
                 sumo_delay: int = 100, sumo_auto_start: bool = True, scenario: str = "normal"):
        super().__init__()
        
        # SUMO connector
        self.use_sumo = use_sumo and SUMO_AVAILABLE
        self.sumo_connector = None
        self.sumo_gui = sumo_gui
        self.sumo_delay = sumo_delay
        self.sumo_auto_start = sumo_auto_start
        
        # Scénario actif
        self.active_scenario = scenario
        
        # Charger la configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # Paramètres de simulation
        self.time_step = self.config['simulation']['time_step']
        self.duration = self.config['simulation']['duration']
        self.current_step = 0
        self.max_steps = int(self.duration / self.time_step)
        
        # Seed pour reproductibilité
        seed = self.config['simulation']['random_seed']
        random.seed(seed)
        np.random.seed(seed)
        
        # Environnement
        self.width = self.config['environment']['width']
        self.height = self.config['environment']['height']
        self.cell_size = self.config['environment']['cell_size']
        
        # Ordonnanceur d'agents (activation aléatoire)
        self.schedule = RandomActivation(self)
        
        # OPTIMISATION: Listes séparées pour accès rapide sans isinstance
        self.vehicle_agents: List[VehicleAgent] = []
        self.intersection_agents: List[IntersectionAgent] = []
        
        # Réseau routier (maillage plus large pour des performances raisonnables)
        self.road_network = RoadNetwork()
        road_cell_size = max(self.cell_size, 100)  # Minimum 100m entre nœuds du réseau
        self.road_network.create_grid_network(self.width, self.height, road_cell_size)
        
        # Routeur
        use_astar = self.config['algorithms']['routing']['algorithm'] == "A_STAR"
        self.router = DynamicRouter(self.road_network, use_astar=use_astar)
        
        # Routeur de messages
        self.message_router = MessageRouter(self)
        
        # Base de données PostgreSQL
        self.use_database = self.config.get('database', {}).get('type') == 'postgresql'
        self.db = None
        self.simulation_id = None
        
        if self.use_database:
            try:
                self.db = PostgreSQLDatabase(config_path)
                # Créer une nouvelle simulation dans la DB
                self.simulation_id = self.db.create_simulation(
                    simulation_name=f"Simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    scenario="default",
                    config=self.config
                )
                logger.info(f"✅ Simulation enregistrée en DB avec ID: {self.simulation_id}")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de se connecter à PostgreSQL: {e}")
                logger.warning("⚠️ La simulation continuera sans base de données")
                self.use_database = False
        
        # Agents
        self.vehicles: List[VehicleAgent] = []
        self.intersections: List[IntersectionAgent] = []
        
        # Statistiques
        self.total_vehicles_created = 0
        self.total_vehicles_arrived = 0
        self.total_travel_time = 0.0
        
        # Algorithme d'optimisation des feux
        self.use_q_learning = (
            self.config['algorithms']['traffic_light']['algorithm'] == "Q_LEARNING"
        )
        
        # Créer les intersections
        self._create_intersections()
        
        # Créer le gestionnaire de crise
        self.crisis_manager = CrisisManagerAgent(
            unique_id="crisis_manager",
            model=self
        )
        self.crisis_manager.position = (self.width // 2, self.height // 2)
        self.schedule.add(self.crisis_manager)
        
        # Initialiser les scénarios selon le scénario actif
        self.rush_hour_info = None
        self.incident_scenario = None
        
        if self.active_scenario in ['rush_hour', 'all']:
            self.rush_hour_info = setup_rush_hour(self)
            logger.info(f"📋 Scénario 'Heure de pointe' initialisé")
        
        if self.active_scenario in ['incident', 'all']:
            self.incident_scenario = IncidentScenario(self)
            self.incident_scenario.setup()
            logger.info(f"📋 Scénario 'Incident Pont De Gaulle' initialisé")
        
        # Créer les véhicules initiaux
        self._create_initial_vehicles()
        
        # Lancer SUMO si demandé
        if self.use_sumo:
            try:
                self.sumo_connector = SumoConnector(
                    use_gui=self.sumo_gui,
                    delay=self.sumo_delay,
                    auto_start=self.sumo_auto_start
                )
                self.sumo_connector.start()
                logger.info("✅ SUMO-GUI connecté")
                
                # Synchronisation initiale des feux de circulation
                # Important : transmettre les états initiaux Mesa → SUMO
                if self.intersections:
                    self.sumo_connector.sync_traffic_lights_from_mesa(self.intersections)
                    logger.info(f"🚦 Synchronisation initiale : {len(self.intersections)} feux configurés")
            except Exception as e:
                logger.warning(f"⚠️ Impossible de lancer SUMO: {e}")
                self.sumo_connector = None
                self.use_sumo = False
        
        # Collecteur de données
        self.datacollector = DataCollector(
            model_reporters={
                "Average_Travel_Time": self._compute_avg_travel_time,
                "Average_Queue_Length": self._compute_avg_queue_length,
                "Total_Messages": lambda m: m.message_router.total_messages_routed,
                "Active_Vehicles": lambda m: len([v for v in m.vehicles if v.active]),
                "Vehicles_Arrived": lambda m: m.total_vehicles_arrived,
                "Average_Speed": self._compute_avg_speed,
                "Congestion_Level": self._compute_congestion_level
            },
            agent_reporters={
                "Speed": lambda a: a.speed if isinstance(a, VehicleAgent) else None,
                "Position": lambda a: a.position if hasattr(a, 'position') else None
            }
        )
    
    def _create_intersections(self):
        """Crée les agents intersection aux carrefours"""
        intersection_spacing = self.width // 5  # ~6 intersections par axe (grille 6×6 = 36 intersections)
        
        intersection_id = 0
        for x in range(0, self.width, intersection_spacing):
            for y in range(0, self.height, intersection_spacing):
                intersection = IntersectionAgent(
                    unique_id=f"intersection_{intersection_id}",
                    model=self,
                    position=(x, y)
                )
                
                self.intersections.append(intersection)
                self.intersection_agents.append(intersection)  # OPTIMISATION: Liste séparée
                self.schedule.add(intersection)
                intersection_id += 1
        
        # Connecter les intersections voisines
        self._connect_neighbor_intersections()
        
        print(f"✅ {len(self.intersections)} intersections créées")
    
    def _connect_neighbor_intersections(self):
        """Connecte les intersections voisines pour la coordination"""
        intersection_spacing = self.width // 5
        neighbor_radius = intersection_spacing * 1.5  # Connecter les voisins directs (adjacents)
        
        for i, intersection in enumerate(self.intersections):
            for other in self.intersections[i+1:]:
                distance = np.sqrt(
                    (intersection.position[0] - other.position[0])**2 +
                    (intersection.position[1] - other.position[1])**2
                )
                
                if distance <= neighbor_radius:
                    intersection.add_neighbor(other)
                    other.add_neighbor(intersection)
    
    def _create_initial_vehicles(self):
        """Crée les véhicules initiaux avec un mix de types réaliste"""
        num_vehicles = self.config['simulation']['num_vehicles']
        
        # Distribution réaliste des types de véhicules
        # 70% standard, 10% bus SOTRA, 5% ambulance, 5% pompier, 5% police, 5% standard supplémentaire
        vehicle_types = []
        for i in range(num_vehicles):
            r = random.random()
            if r < 0.70:
                vehicle_types.append("standard")
            elif r < 0.80:
                vehicle_types.append("bus_sotra")
            elif r < 0.85:
                vehicle_types.append("ambulance")
            elif r < 0.90:
                vehicle_types.append("pompier")
            elif r < 0.95:
                vehicle_types.append("police")
            else:
                vehicle_types.append("standard")
        
        for i in range(num_vehicles):
            self._create_vehicle(f"vehicle_{i}", vehicle_type=vehicle_types[i])
        
        # Compter par type
        from collections import Counter
        counts = Counter(vehicle_types)
        print(f"✅ {num_vehicles} véhicules créés: {dict(counts)}")
    
    def _create_vehicle(self, vehicle_id: str = None, vehicle_type: str = "standard",
                        start_pos: Tuple[float, float] = None,
                        dest_pos: Tuple[float, float] = None,
                        use_gps_coords: bool = False):
        """
        Crée un nouveau véhicule avec origine et destination.
        
        Args:
            vehicle_id: ID unique du véhicule
            vehicle_type: Type de véhicule (standard, ambulance, etc.)
            start_pos: Position de départ (x,y) ou (lon,lat) si use_gps_coords=True
            dest_pos: Position de destination (x,y) ou (lon,lat) si use_gps_coords=True
            use_gps_coords: Si True, start_pos et dest_pos sont des coordonnées GPS (lon,lat)
        """
        if vehicle_id is None:
            vehicle_id = f"vehicle_{self.total_vehicles_created}"
        
        if start_pos is None:
            # Position de départ aléatoire
            start_x = random.randint(0, self.width - 1)
            start_y = random.randint(0, self.height - 1)
            start_pos = (start_x, start_y)
        
        if dest_pos is None:
            # Destination aléatoire (différente de l'origine)
            while True:
                dest_x = random.randint(0, self.width - 1)
                dest_y = random.randint(0, self.height - 1)
                dest_pos = (dest_x, dest_y)
                
                # S'assurer que la destination est assez loin
                distance = np.sqrt((dest_pos[0] - start_pos[0])**2 + (dest_pos[1] - start_pos[1])**2)
                if distance > self.width * 0.3:  # Au moins 30% de la largeur
                    break
        
        # Vitesse max selon le type de véhicule
        speed_by_type = {
            "standard": self.config['vehicle']['max_speed'],
            "ambulance": 22.22,   # 80 km/h
            "bus_sotra": 11.11,   # 40 km/h
            "pompier": 19.44,     # 70 km/h
            "police": 22.22,      # 80 km/h
        }
        max_speed = speed_by_type.get(vehicle_type, self.config['vehicle']['max_speed'])
        
        # Créer le véhicule
        vehicle = VehicleAgent(
            unique_id=vehicle_id,
            model=self,
            position=start_pos,
            destination=dest_pos,
            max_speed=max_speed,
            vehicle_type=vehicle_type
        )
        
        # Calculer la route initiale
        route = self.calculate_route(start_pos, dest_pos)
        if route:
            vehicle.current_route = route
        
        self.vehicles.append(vehicle)
        self.vehicle_agents.append(vehicle)  # OPTIMISATION: Liste séparée
        self.schedule.add(vehicle)
        self.total_vehicles_created += 1
        
        # Ajouter le véhicule à SUMO si activé
        if self.use_sumo and self.sumo_connector:
            if use_gps_coords:
                # Utiliser les coordonnées GPS (lon, lat)
                success = self.sumo_connector.add_vehicle(
                    mesa_vehicle_id=vehicle_id,
                    vehicle_type=vehicle_type,
                    origin_coords=start_pos,
                    dest_coords=dest_pos
                )
                if not success:
                    logger.debug(f"⚠️ Échec ajout SUMO pour {vehicle_id} - GPS: {start_pos} → {dest_pos}")
            else:
                # Utiliser les edges aléatoires (mode grille)
                self.sumo_connector.add_vehicle(
                    mesa_vehicle_id=vehicle_id,
                    vehicle_type=vehicle_type
                )
        
        return vehicle
    
    def calculate_route(self, start: Tuple[float, float], 
                       end: Tuple[float, float]) -> List[Tuple[float, float]]:
        """Calcule une route entre deux points"""
        return self.router.find_path(start, end, consider_traffic=True)
    
    def get_agent_by_id(self, agent_id: str):
        """Récupère un agent par son ID"""
        for agent in self.schedule.agents:
            if agent.unique_id == agent_id:
                return agent
        return None
    
    def step(self):
        """
        Effectue un pas de simulation
        """
        # Visualiser les zones géographiques au premier step (après init SUMO-GUI)
        if self.current_step == 0 and self.use_sumo and self.sumo_connector:
            if self.active_scenario in ['rush_hour', 'all']:
                self.sumo_connector.visualize_geographic_zones()
        
        # Router les messages en attente
        self._route_pending_messages()
        
        # Activer tous les agents
        self.schedule.step()
        
        # Vérifier les véhicules arrivés
        self._check_arrived_vehicles()
        
        # Exécuter les scénarios
        self._run_scenarios()
        
        # Collecter les données
        self.datacollector.collect(self)
        
        # Sauvegarder les KPIs dans PostgreSQL
        if self.use_database and self.db and self.current_step % 10 == 0:  # Toutes les 10 secondes
            try:
                current_kpis = {
                    'Average_Travel_Time': self._compute_avg_travel_time(),
                    'Average_Queue_Length': self._compute_avg_queue_length(),
                    'Total_Messages': self.message_router.total_messages_routed,
                    'Active_Vehicles': len([v for v in self.vehicles if v.active]),
                    'Vehicles_Arrived': self.total_vehicles_arrived,
                    'Average_Speed': self._compute_avg_speed(),
                    'Congestion_Level': self._compute_congestion_level()
                }
                self.db.insert_kpi_snapshot(self.simulation_id, self.current_step, current_kpis)
            except Exception as e:
                logger.warning(f"⚠️ Erreur sauvegarde KPIs: {e}")
        
        # Synchroniser avec SUMO
        if self.use_sumo and self.sumo_connector:
            self.sumo_connector.sync_step(self)
        
        # Incrémenter le compteur
        self.current_step += 1
    
    def _route_pending_messages(self):
        """Route tous les messages en attente"""
        for agent in self.schedule.agents:
            while agent.message_outbox:
                message = agent.message_outbox.pop(0)
                self.message_router.route_message(message)
    
    def _check_arrived_vehicles(self):
        """Vérifie et retire les véhicules arrivés"""
        arrived = []
        for vehicle in self.vehicles:
            if not vehicle.active:
                arrived.append(vehicle)
                self.total_vehicles_arrived += 1
                self.total_travel_time += vehicle.travel_time
        
        # Retirer les véhicules arrivés
        for vehicle in arrived:
            self.vehicles.remove(vehicle)
            self.vehicle_agents.remove(vehicle)  # OPTIMISATION: Retirer aussi de la liste séparée
            self.schedule.remove(vehicle)
    
    def _run_scenarios(self):
        """Exécute les scénarios actifs à chaque pas de simulation"""
        # Scénario 1 : Heure de pointe (utilise le module scenarios/rush_hour.py)
        if self.rush_hour_info is not None:
            rush_hour_step(self, self.rush_hour_info)
        
        # Scénario 2 : Incident Pont De Gaulle (utilise scenarios/incident.py)
        if self.incident_scenario is not None:
            self.incident_scenario.step(self.current_step)
    
    # ============ REPORTERS POUR DATACOLLECTOR ============
    
    def _compute_avg_travel_time(self) -> float:
        """Calcule le temps de trajet moyen"""
        if not self.vehicles:
            return 0.0
        active_travel_times = [v.travel_time for v in self.vehicles if v.active]
        return sum(active_travel_times) / len(active_travel_times) if active_travel_times else 0.0
    
    def _compute_avg_queue_length(self) -> float:
        """Calcule la longueur moyenne des files d'attente"""
        if not self.intersections:
            return 0.0
        total_queue = sum(sum(i.queue_lengths.values()) for i in self.intersections)
        return total_queue / len(self.intersections)
    
    def _compute_avg_speed(self) -> float:
        """Calcule la vitesse moyenne des véhicules"""
        if not self.vehicles:
            return 0.0
        active_speeds = [v.speed for v in self.vehicles if v.active]
        return sum(active_speeds) / len(active_speeds) if active_speeds else 0.0
    
    def _compute_congestion_level(self) -> float:
        """Calcule le niveau de congestion global (0-1)"""
        if not self.vehicles:
            return 0.0
        # Basé sur le ratio vitesse moyenne / vitesse max
        avg_speed = self._compute_avg_speed()
        max_speed = self.config['vehicle']['max_speed']
        return 1.0 - (avg_speed / max_speed) if max_speed > 0 else 0.0
    
    # ============ MÉTHODES UTILITAIRES ============

    def get_agent_by_id(self, agent_id: str):
        """Retourne un agent par son unique_id, ou None s'il n'existe pas"""
        for agent in self.schedule.agents:
            if agent.unique_id == agent_id:
                return agent
        return None

    def get_statistics(self) -> Dict:
        """Retourne les statistiques complètes de la simulation"""
        stats = {
            'simulation': {
                'current_step': self.current_step,
                'elapsed_time': self.current_step * self.time_step,
                'total_vehicles_created': self.total_vehicles_created,
                'total_vehicles_arrived': self.total_vehicles_arrived,
                'active_vehicles': len([v for v in self.vehicles if v.active])
            },
            'performance': {
                'average_travel_time': self._compute_avg_travel_time(),
                'average_queue_length': self._compute_avg_queue_length(),
                'average_speed': self._compute_avg_speed(),
                'congestion_level': self._compute_congestion_level()
            },
            'communication': self.message_router.get_statistics(),
            'network': self.road_network.get_statistics(),
            'crisis_manager': self.crisis_manager.get_statistics(),
            'coordination': self._compute_coordination_stats(),
            'scenarios': {
                'rush_hour': {
                    'vehicles_created': self.rush_hour_info.get('vehicles_created', 0) if self.rush_hour_info else 0
                },
                'incident': self.incident_scenario.get_statistics() if self.incident_scenario else {}
            }
        }
        return stats

    def _compute_coordination_stats(self) -> Dict:
        """Calcule les statistiques globales de coordination de voisinage"""
        from agents.intersection_agent import IntersectionAgent
        total_coord_messages = 0
        total_green_waves    = 0
        active_green_waves   = 0
        total_neighbor_links = 0

        for agent in self.schedule.agents:
            if isinstance(agent, IntersectionAgent):
                total_coord_messages += agent.coordination_messages_sent
                total_neighbor_links += len(agent.neighbors)
                if agent._green_wave_active:
                    active_green_waves += 1

        return {
            'total_coordination_messages': total_coord_messages,
            'active_green_waves': active_green_waves,
            'total_neighbor_links': total_neighbor_links // 2,  # chaque lien compté 2 fois
        }
    
    def run_simulation(self, steps: int = None):
        """Exécute la simulation pour un nombre de pas donné"""
        if steps is None:
            steps = self.max_steps
        
        print(f"\n🚀 Démarrage de la simulation ({steps} steps)...\n")
        
        for i in range(steps):
            self.step()
            
            # Afficher la progression
            if (i + 1) % 100 == 0:
                print(f"Step {i + 1}/{steps} - "
                      f"Véhicules actifs: {len([v for v in self.vehicles if v.active])} - "
                      f"Vitesse moy: {self._compute_avg_speed():.2f} m/s")
        
        print(f"\n✅ Simulation terminée !\n")
        
        # Sauvegarder les résultats finaux dans PostgreSQL
        if self.use_database and self.db:
            try:
                logger.info("💾 Sauvegarde des résultats dans PostgreSQL...")
                
                # Sauvegarder tous les véhicules
                vehicles_data = []
                for vehicle in self.vehicles:
                    stats = vehicle.get_statistics()
                    stats['origin_x'] = vehicle.origin[0]
                    stats['origin_y'] = vehicle.origin[1]
                    stats['destination_x'] = vehicle.destination[0]
                    stats['destination_y'] = vehicle.destination[1]
                    vehicles_data.append(stats)
                
                if vehicles_data:
                    self.db.insert_vehicles_batch(self.simulation_id, vehicles_data)
                    logger.info(f"  ✅ {len(vehicles_data)} véhicules sauvegardés")
                
                # Sauvegarder toutes les intersections
                for intersection in self.intersections:
                    self.db.insert_intersection(self.simulation_id, intersection.get_statistics())
                
                logger.info(f"  ✅ {len(self.intersections)} intersections sauvegardées")
                
                # Mettre à jour le nombre d'intersections et terminer la simulation
                self.db.update_simulation(
                    self.simulation_id,
                    num_intersections=len(self.intersections)
                )
                self.db.end_simulation(self.simulation_id, self.current_step * self.time_step)
                
                logger.success(f"✅ Simulation {self.simulation_id} sauvegardée en base de données")
                
            except Exception as e:
                logger.error(f"❌ Erreur lors de la sauvegarde finale: {e}")
        
        # Fermer SUMO si connecté
        if self.use_sumo and self.sumo_connector:
            self.sumo_connector.close()
        
        print("📊 Statistiques finales:")
        stats = self.get_statistics()
        for category, values in stats.items():
            print(f"\n  {category.upper()}:")
            for key, value in values.items():
                print(f"    - {key}: {value}")
