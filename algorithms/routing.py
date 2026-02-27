"""
Algorithmes de routage pour les véhicules
Implémentation de A* et Dijkstra
"""
import heapq
import math
from typing import Tuple, List, Dict, Set, Optional, Callable
import networkx as nx


class Node:
    """Représente un nœud dans le graphe de routes"""
    
    def __init__(self, position: Tuple[float, float], node_id: str = None):
        self.position = position
        self.id = node_id if node_id else f"{position[0]}_{position[1]}"
        self.neighbors: Dict[str, float] = {}  # {neighbor_id: distance}
    
    def add_neighbor(self, neighbor_id: str, distance: float):
        """Ajoute un voisin"""
        self.neighbors[neighbor_id] = distance
    
    def __repr__(self):
        return f"Node({self.id}, pos={self.position})"
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        return self.id == other.id


class RoadNetwork:
    """
    Représente le réseau routier
    """
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.graph = nx.Graph()
        self.grid_size = 100  # Taille de la grille pour discrétisation
    
    def add_node(self, node: Node):
        """Ajoute un nœud au réseau"""
        self.nodes[node.id] = node
        self.graph.add_node(node.id, pos=node.position)
    
    def add_edge(self, node1_id: str, node2_id: str, weight: float = None):
        """Ajoute une arête entre deux nœuds"""
        if node1_id not in self.nodes or node2_id not in self.nodes:
            return False
        
        if weight is None:
            # Calculer la distance euclidienne
            pos1 = self.nodes[node1_id].position
            pos2 = self.nodes[node2_id].position
            weight = self._euclidean_distance(pos1, pos2)
        
        self.nodes[node1_id].add_neighbor(node2_id, weight)
        self.nodes[node2_id].add_neighbor(node1_id, weight)
        self.graph.add_edge(node1_id, node2_id, weight=weight)
        
        return True
    
    def create_grid_network(self, width: int, height: int, cell_size: int = 100):
        """
        Crée un réseau en grille
        Utile pour la simulation urbaine
        """
        self.grid_size = cell_size
        
        # Créer les nœuds de la grille
        for x in range(0, width, cell_size):
            for y in range(0, height, cell_size):
                node = Node((x, y))
                self.add_node(node)
        
        # Connecter les nœuds adjacents
        for x in range(0, width, cell_size):
            for y in range(0, height, cell_size):
                current_id = f"{x}_{y}"
                
                # Connecter à droite
                if x + cell_size < width:
                    right_id = f"{x + cell_size}_{y}"
                    self.add_edge(current_id, right_id)
                
                # Connecter en bas
                if y + cell_size < height:
                    down_id = f"{x}_{y + cell_size}"
                    self.add_edge(current_id, down_id)
    
    def get_nearest_node(self, position: Tuple[float, float]) -> Optional[Node]:
        """Trouve le nœud le plus proche d'une position"""
        if not self.nodes:
            return None
        
        min_distance = float('inf')
        nearest_node = None
        
        for node in self.nodes.values():
            distance = self._euclidean_distance(position, node.position)
            if distance < min_distance:
                min_distance = distance
                nearest_node = node
        
        return nearest_node
    
    def get_node_at_position(self, position: Tuple[float, float], 
                            tolerance: float = 10.0) -> Optional[Node]:
        """Récupère un nœud à une position donnée (avec tolérance)"""
        for node in self.nodes.values():
            if self._euclidean_distance(position, node.position) < tolerance:
                return node
        return None
    
    def remove_edge(self, node1_id: str, node2_id: str):
        """Supprime une arête (pour simuler des blocages)"""
        if node1_id in self.nodes and node2_id in self.nodes:
            self.nodes[node1_id].neighbors.pop(node2_id, None)
            self.nodes[node2_id].neighbors.pop(node1_id, None)
            if self.graph.has_edge(node1_id, node2_id):
                self.graph.remove_edge(node1_id, node2_id)
    
    def add_temporary_blockage(self, node1_id: str, node2_id: str, duration: float):
        """
        Bloque temporairement une route.
        Le blocage est enregistré avec son heure d'expiration.
        Appeler restore_expired_blockages() à chaque step pour restaurer automatiquement.
        """
        if not hasattr(self, '_temporary_blockages'):
            self._temporary_blockages: List[Tuple[str, str, float]] = []
        self.remove_edge(node1_id, node2_id)
        # Stocker (node1, node2, expiration_time) — expiration_time doit être comparé
        # à un compteur externe (ex: model.current_step * model.time_step)
        self._temporary_blockages.append((node1_id, node2_id, duration))

    def restore_expired_blockages(self, current_time: float):
        """
        Restaure les arêtes dont le blocage temporaire a expiré.
        Doit être appelé à chaque step avec le temps courant de la simulation.
        """
        if not hasattr(self, '_temporary_blockages'):
            return
        still_blocked = []
        for node1_id, node2_id, expiry in self._temporary_blockages:
            if current_time >= expiry:
                self.add_edge(node1_id, node2_id)
            else:
                still_blocked.append((node1_id, node2_id, expiry))
        self._temporary_blockages = still_blocked
    
    @staticmethod
    def _euclidean_distance(pos1: Tuple[float, float], 
                           pos2: Tuple[float, float]) -> float:
        """Calcule la distance euclidienne"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def get_statistics(self) -> Dict:
        """Retourne des statistiques sur le réseau"""
        return {
            'num_nodes': len(self.nodes),
            'num_edges': self.graph.number_of_edges(),
            'average_degree': sum(len(n.neighbors) for n in self.nodes.values()) / max(len(self.nodes), 1)
        }


class AStarRouter:
    """
    Implémentation de l'algorithme A* pour le routage
    Optimisé pour réseaux OSM réels avec cache LRU
    """
    
    def __init__(self, network: RoadNetwork, cache_size: int = 200):
        self.network = network
        self.paths_calculated = 0
        
        # Cache LRU pour routes fréquentes (optimisation OSM)
        self.route_cache: Dict[Tuple[str, str], List[str]] = {}
        self.cache_size = cache_size
        self.cache_hits = 0
        self.cache_misses = 0
    
    def find_path(self, start_pos: Tuple[float, float], 
                  end_pos: Tuple[float, float]) -> Optional[List[Tuple[float, float]]]:
        """
        Trouve le chemin optimal de start à end en utilisant A*
        Utilise un cache LRU pour optimiser les routes fréquentes (réseaux OSM)
        
        Returns:
            Liste de positions (waypoints) ou None si pas de chemin
        """
        # Trouver les nœuds les plus proches
        start_node = self.network.get_nearest_node(start_pos)
        end_node = self.network.get_nearest_node(end_pos)
        
        if not start_node or not end_node:
            return None
        
        # Si déjà au même nœud
        if start_node.id == end_node.id:
            return [start_pos, end_pos]
        
        # Vérifier le cache (optimisation OSM)
        cache_key = (start_node.id, end_node.id)
        if cache_key in self.route_cache:
            self.cache_hits += 1
            path = self.route_cache[cache_key]
        else:
            # A* Algorithm
            self.cache_misses += 1
            path = self._a_star(start_node.id, end_node.id)
            
            # Ajouter au cache si trouvé
            if path:
                self._add_to_cache(cache_key, path)
        
        if path:
            self.paths_calculated += 1
            # Convertir les IDs de nœuds en positions
            waypoints = [start_pos]  # Commencer par la position réelle
            waypoints.extend([self.network.nodes[node_id].position for node_id in path[1:-1]])
            waypoints.append(end_pos)  # Finir par la destination réelle
            return waypoints
        
        return None
    
    def _a_star(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """
        Implémentation de A* optimisée pour réseaux OSM réels.
        
        Améliorations:
        - Heuristique adaptative pour réseaux non-euclidiens
        - Facteur de correction pour routes sinueuses
        - Optimisation pour grandes distances
        
        Returns:
            Liste d'IDs de nœuds formant le chemin
        """
        # Heuristique adaptative pour réseaux OSM réels
        def heuristic(node_id: str) -> float:
            node_pos = self.network.nodes[node_id].position
            end_pos = self.network.nodes[end_id].position
            euclidean_dist = self.network._euclidean_distance(node_pos, end_pos)
            
            # Facteur de correction pour réseaux OSM (routes non-rectilignes)
            # Les routes réelles sont rarement en ligne droite
            # Facteur typique: 1.2-1.4 pour zones urbaines
            osm_correction_factor = 1.3
            
            # Pour grandes distances, réduire le facteur (autoroutes plus directes)
            if euclidean_dist > 5000:  # > 5km
                osm_correction_factor = 1.15
            elif euclidean_dist > 10000:  # > 10km
                osm_correction_factor = 1.1
            
            return euclidean_dist * osm_correction_factor
        
        # Priority queue: (f_score, node_id)
        open_set = []
        heapq.heappush(open_set, (0, start_id))
        
        # Dictionnaires pour A*
        came_from: Dict[str, str] = {}
        g_score: Dict[str, float] = {start_id: 0}
        f_score: Dict[str, float] = {start_id: heuristic(start_id)}
        
        # Ensemble des nœuds déjà évalués
        closed_set: Set[str] = set()
        
        while open_set:
            # Récupérer le nœud avec le plus petit f_score
            current_f, current_id = heapq.heappop(open_set)
            
            # Si on a atteint la destination
            if current_id == end_id:
                return self._reconstruct_path(came_from, current_id)
            
            # Marquer comme évalué
            closed_set.add(current_id)
            
            # Explorer les voisins
            current_node = self.network.nodes[current_id]
            for neighbor_id, edge_weight in current_node.neighbors.items():
                if neighbor_id in closed_set:
                    continue
                
                # Calculer le tentative g_score
                tentative_g = g_score[current_id] + edge_weight
                
                # Si ce chemin est meilleur
                if neighbor_id not in g_score or tentative_g < g_score[neighbor_id]:
                    came_from[neighbor_id] = current_id
                    g_score[neighbor_id] = tentative_g
                    f_score[neighbor_id] = tentative_g + heuristic(neighbor_id)
                    
                    # Ajouter à open_set si pas déjà présent
                    if neighbor_id not in [item[1] for item in open_set]:
                        heapq.heappush(open_set, (f_score[neighbor_id], neighbor_id))
        
        # Pas de chemin trouvé
        return None
    
    def _reconstruct_path(self, came_from: Dict[str, str], current_id: str) -> List[str]:
        """Reconstruit le chemin depuis came_from"""
        path = [current_id]
        while current_id in came_from:
            current_id = came_from[current_id]
            path.append(current_id)
        path.reverse()
        return path
    
    def _add_to_cache(self, cache_key: Tuple[str, str], path: List[str]):
        """
        Ajoute une route au cache avec politique LRU (Least Recently Used).
        Si le cache est plein, supprime l'entrée la plus ancienne.
        """
        # Si le cache est plein, supprimer la plus ancienne entrée
        if len(self.route_cache) >= self.cache_size:
            # Supprimer le premier élément (le plus ancien)
            oldest_key = next(iter(self.route_cache))
            del self.route_cache[oldest_key]
        
        # Ajouter la nouvelle route
        self.route_cache[cache_key] = path
    
    def get_cache_statistics(self) -> Dict:
        """Retourne les statistiques du cache pour analyse de performance"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = (self.cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.route_cache),
            'cache_capacity': self.cache_size,
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'hit_rate_percent': round(hit_rate, 2),
            'paths_calculated': self.paths_calculated
        }


class DijkstraRouter:
    """
    Implémentation de l'algorithme de Dijkstra pour le routage
    """
    
    def __init__(self, network: RoadNetwork):
        self.network = network
        self.paths_calculated = 0
    
    def find_path(self, start_pos: Tuple[float, float], 
                  end_pos: Tuple[float, float]) -> Optional[List[Tuple[float, float]]]:
        """
        Trouve le chemin optimal de start à end en utilisant Dijkstra
        """
        # Trouver les nœuds les plus proches
        start_node = self.network.get_nearest_node(start_pos)
        end_node = self.network.get_nearest_node(end_pos)
        
        if not start_node or not end_node:
            return None
        
        if start_node.id == end_node.id:
            return [start_pos, end_pos]
        
        # Dijkstra Algorithm
        path = self._dijkstra(start_node.id, end_node.id)
        
        if path:
            self.paths_calculated += 1
            waypoints = [start_pos]
            waypoints.extend([self.network.nodes[node_id].position for node_id in path[1:-1]])
            waypoints.append(end_pos)
            return waypoints
        
        return None
    
    def _dijkstra(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """
        Implémentation de Dijkstra
        """
        # Priority queue: (distance, node_id)
        pq = []
        heapq.heappush(pq, (0, start_id))
        
        # Distances et prédécesseurs
        distances: Dict[str, float] = {start_id: 0}
        came_from: Dict[str, str] = {}
        visited: Set[str] = set()
        
        while pq:
            current_dist, current_id = heapq.heappop(pq)
            
            # Si déjà visité avec une meilleure distance
            if current_id in visited:
                continue
            
            visited.add(current_id)
            
            # Si destination atteinte
            if current_id == end_id:
                return self._reconstruct_path(came_from, current_id)
            
            # Explorer les voisins
            current_node = self.network.nodes[current_id]
            for neighbor_id, edge_weight in current_node.neighbors.items():
                if neighbor_id in visited:
                    continue
                
                new_distance = current_dist + edge_weight
                
                if neighbor_id not in distances or new_distance < distances[neighbor_id]:
                    distances[neighbor_id] = new_distance
                    came_from[neighbor_id] = current_id
                    heapq.heappush(pq, (new_distance, neighbor_id))
        
        return None
    
    def _reconstruct_path(self, came_from: Dict[str, str], current_id: str) -> List[str]:
        """Reconstruit le chemin"""
        path = [current_id]
        while current_id in came_from:
            current_id = came_from[current_id]
            path.append(current_id)
        path.reverse()
        return path


class DynamicRouter:
    """
    Routeur dynamique qui prend en compte les conditions de trafic
    """
    
    def __init__(self, network: RoadNetwork, use_astar: bool = True):
        self.network = network
        self.router = AStarRouter(network) if use_astar else DijkstraRouter(network)
        self.traffic_weights: Dict[Tuple[str, str], float] = {}
    
    def update_traffic_weight(self, node1_id: str, node2_id: str, congestion_factor: float):
        """
        Met à jour le poids d'une route basé sur la congestion
        congestion_factor: 1.0 = normal, >1.0 = congestionné
        """
        edge_key = tuple(sorted([node1_id, node2_id]))
        self.traffic_weights[edge_key] = congestion_factor
    
    def find_path(self, start_pos: Tuple[float, float], 
                  end_pos: Tuple[float, float],
                  consider_traffic: bool = True) -> Optional[List[Tuple[float, float]]]:
        """
        Trouve un chemin en tenant compte éventuellement du trafic
        """
        if consider_traffic and self.traffic_weights:
            # Créer un réseau temporaire avec les poids ajustés
            temp_network = self._create_weighted_network()
            temp_router = AStarRouter(temp_network)
            return temp_router.find_path(start_pos, end_pos)
        else:
            return self.router.find_path(start_pos, end_pos)
    
    def _create_weighted_network(self) -> RoadNetwork:
        """Crée un réseau avec les poids de trafic"""
        temp_network = RoadNetwork()
        temp_network.nodes = self.network.nodes.copy()
        temp_network.graph = self.network.graph.copy()
        
        # Ajuster les poids
        for (node1_id, node2_id), congestion in self.traffic_weights.items():
            if node1_id in temp_network.nodes and node2_id in temp_network.nodes:
                base_weight = self.network.nodes[node1_id].neighbors.get(node2_id, 1.0)
                adjusted_weight = base_weight * congestion
                temp_network.nodes[node1_id].neighbors[node2_id] = adjusted_weight
                temp_network.nodes[node2_id].neighbors[node1_id] = adjusted_weight
        
        return temp_network
