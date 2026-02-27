"""
Scénario 2 : Incident localisé
Simulation d'une panne de véhicule sur le Pont De Gaulle
et observation de la capacité du système à rediriger les flux vers le Pont HKB
"""
import random
from typing import Dict, List, Tuple, Optional
from loguru import logger


class IncidentScenario:
    """
    Gère le scénario d'incident sur le Pont De Gaulle.
    
    Déroulement:
        1. La simulation tourne normalement pendant 30 minutes
        2. À t=1800s, un incident bloque le Pont De Gaulle
        3. Les intersections détectent la congestion et diffusent l'info
        4. Les véhicules recalculent leurs routes vers le Pont HKB
        5. Après 15 minutes (t=2700s), l'incident est résolu
    
    Métriques observées:
        - Temps de réaction du système (détection + redirection)
        - Augmentation du trafic sur le Pont HKB
        - Temps de trajet moyen avant/pendant/après l'incident
    """
    
    def __init__(self, model, config: Dict = None):
        self.model = model
        
        if config is None:
            config = model.config.get('scenarios', {}).get('incident_bridge', {})
        
        self.name = config.get('name', 'Incident Pont De Gaulle')
        self.description = config.get('description', 
            'Panne véhicule sur Pont De Gaulle -> redirection Pont HKB')
        
        # Timing de l'incident
        self.incident_start_time = config.get('start_time', 1800)
        self.incident_duration = config.get('duration', 900)
        self.incident_end_time = self.incident_start_time + self.incident_duration
        
        # Routes concernées
        blocked_road = config.get('blocked_road', {})
        self.blocked_road_name = blocked_road.get('name', 'Pont De Gaulle')
        self.blocked_road_coords = blocked_road.get('coordinates', 
            [[2500, 2000], [2500, 2500]])
        
        alternative_road = config.get('alternative_road', {})
        self.alternative_road_name = alternative_road.get('name', 'Pont HKB')
        self.alternative_road_coords = alternative_road.get('coordinates',
            [[3000, 2000], [3000, 2500]])
        
        # État de l'incident
        self.incident_active = False
        self.incident_resolved = False  # Flag pour éviter de re-déclencher après résolution
        self.blocked_edges: List[Tuple[str, str]] = []
        
        # Métriques spécifiques au scénario
        self.metrics = {
            'avg_travel_time_before': [],
            'avg_travel_time_during': [],
            'avg_travel_time_after': [],
            'vehicles_redirected': 0,
            'detection_time': None,
            'congestion_messages_sent': 0
        }
    
    def setup(self):
        """Configure le scénario (appelé au début de la simulation)"""
        logger.info(f"📋 Scénario '{self.name}' configuré")
        logger.info(f"   Incident prévu à t={self.incident_start_time}s "
                    f"(durée: {self.incident_duration}s)")
        logger.info(f"   Route bloquée: {self.blocked_road_name}")
        logger.info(f"   Route alternative: {self.alternative_road_name}")
    
    def step(self, current_step: int):
        """
        Exécute un pas du scénario d'incident.
        Appelé à chaque step de la simulation.
        """
        current_time = current_step * self.model.time_step
        
        # Collecter les métriques de temps de trajet
        self._collect_travel_time_metrics(current_time)
        
        # Phase 1 : Avant l'incident - rien de spécial
        if current_time < self.incident_start_time:
            return
        
        # Phase 2 : Déclencher l'incident (une seule fois)
        if current_time >= self.incident_start_time and not self.incident_active and not self.incident_resolved:
            self._trigger_incident()
        
        # Phase 3 : Pendant l'incident - surveiller la redirection
        if self.incident_active and current_time < self.incident_end_time:
            self._monitor_during_incident(current_time)
        
        # Phase 4 : Résoudre l'incident
        if self.incident_active and current_time >= self.incident_end_time:
            self._resolve_incident()
    
    def _trigger_incident(self):
        """Déclenche l'incident : bloque les arêtes du Pont De Gaulle"""
        logger.warning(f"🚨 INCIDENT DÉCLENCHÉ : {self.blocked_road_name}")
        
        self.incident_active = True
        
        # Identifier et bloquer les arêtes du réseau routier correspondant au pont
        coords = self.blocked_road_coords
        start_coord = coords[0]
        end_coord = coords[1]
        
        # Trouver les nœuds du réseau proches des coordonnées du pont
        network = self.model.road_network
        
        start_node = network.get_nearest_node(tuple(start_coord))
        end_node = network.get_nearest_node(tuple(end_coord))
        
        if start_node and end_node:
            # Bloquer les arêtes entre les nœuds du pont
            self._block_path_between(start_node.id, end_node.id)
            logger.info(f"   🚧 Route bloquée entre {start_node.id} et {end_node.id}")
        
        # Visualiser le Pont De Gaulle en rouge dans SUMO-GUI
        if self.model.sumo_connector:
            # Forcer explicitement bridge_col=2 pour le Pont De Gaulle
            self.model.sumo_connector.highlight_pont_de_gaulle(highlight=True, rows=6, bridge_col=2)
        
        # Informer le gestionnaire de crise s'il existe
        self._notify_crisis_manager()
        
        # Diffuser l'information de blocage aux intersections proches
        self._broadcast_incident_info()
    
    def _block_path_between(self, start_id: str, end_id: str):
        """Bloque toutes les arêtes entre deux nœuds (et les nœuds intermédiaires)"""
        network = self.model.road_network
        
        start_node = network.nodes.get(start_id)
        end_node = network.nodes.get(end_id)
        
        if not start_node or not end_node:
            return
        
        # Bloquer l'arête directe si elle existe
        if end_id in start_node.neighbors:
            network.remove_edge(start_id, end_id)
            self.blocked_edges.append((start_id, end_id))
        
        # Bloquer aussi les arêtes intermédiaires dans la zone du pont
        start_pos = start_node.position
        end_pos = end_node.position
        
        # Trouver tous les nœuds dans la zone du pont
        min_x = min(start_pos[0], end_pos[0]) - 50
        max_x = max(start_pos[0], end_pos[0]) + 50
        min_y = min(start_pos[1], end_pos[1]) - 50
        max_y = max(start_pos[1], end_pos[1]) + 50
        
        nodes_in_zone = []
        for node_id, node in network.nodes.items():
            if (min_x <= node.position[0] <= max_x and 
                min_y <= node.position[1] <= max_y):
                nodes_in_zone.append(node_id)
        
        # Bloquer les arêtes entre les nœuds de la zone
        for i, node1_id in enumerate(nodes_in_zone):
            for node2_id in nodes_in_zone[i+1:]:
                if node2_id in network.nodes[node1_id].neighbors:
                    network.remove_edge(node1_id, node2_id)
                    self.blocked_edges.append((node1_id, node2_id))
        
        logger.info(f"   🚧 {len(self.blocked_edges)} arêtes bloquées")
    
    def _notify_crisis_manager(self):
        """Notifie le gestionnaire de crise de l'incident"""
        from communication.fipa_message import FIPAMessage
        from agents.crisis_manager_agent import CrisisManagerAgent
        
        for agent in self.model.schedule.agents:
            if isinstance(agent, CrisisManagerAgent):
                message = FIPAMessage(
                    sender="scenario_manager",
                    receiver=agent.unique_id,
                    performative="inform",
                    content={
                        "type": "incident_report",
                        "incident_type": "vehicle_breakdown",
                        "location": self.blocked_road_coords[0],
                        "severity": "high",
                        "road_name": self.blocked_road_name,
                        "alternative_road": self.alternative_road_name
                    },
                    protocol="incident-management"
                )
                agent.receive_message(message)
                break
    
    def _broadcast_incident_info(self):
        """Diffuse l'information de l'incident aux intersections proches"""
        from communication.fipa_message import FIPAMessage
        from agents.intersection_agent import IntersectionAgent
        
        incident_center = (
            (self.blocked_road_coords[0][0] + self.blocked_road_coords[1][0]) / 2,
            (self.blocked_road_coords[0][1] + self.blocked_road_coords[1][1]) / 2
        )
        
        broadcast_radius = 1000.0  # 1km autour de l'incident
        
        for agent in self.model.schedule.agents:
            if isinstance(agent, IntersectionAgent):
                import math
                distance = math.sqrt(
                    (agent.position[0] - incident_center[0])**2 +
                    (agent.position[1] - incident_center[1])**2
                )
                
                if distance <= broadcast_radius:
                    message = FIPAMessage(
                        sender="scenario_manager",
                        receiver=agent.unique_id,
                        performative="inform",
                        content={
                            "type": "congestion",
                            "congestion_level": 1.0,
                            "location": incident_center,
                            "reason": "incident",
                            "blocked_road": self.blocked_road_name
                        }
                    )
                    agent.receive_message(message)
                    self.metrics['congestion_messages_sent'] += 1
        
        # Aussi informer les véhicules proches pour qu'ils recalculent
        from agents.vehicle_agent import VehicleAgent
        for agent in self.model.schedule.agents:
            if isinstance(agent, VehicleAgent) and agent.active:
                import math
                distance = math.sqrt(
                    (agent.position[0] - incident_center[0])**2 +
                    (agent.position[1] - incident_center[1])**2
                )
                
                if distance <= broadcast_radius:
                    message = FIPAMessage(
                        sender="scenario_manager",
                        receiver=agent.unique_id,
                        performative="inform",
                        content={
                            "type": "congestion",
                            "congestion_level": 1.0,
                            "location": incident_center,
                            "reason": "incident",
                            "blocked_road": self.blocked_road_name
                        }
                    )
                    agent.receive_message(message)
                    self.metrics['vehicles_redirected'] += 1
    
    def _monitor_during_incident(self, current_time: float):
        """Surveille l'état du trafic pendant l'incident"""
        # Toutes les 60 secondes, re-diffuser l'info aux intersections uniquement
        # (pas aux véhicules pour ne pas gonfler vehicles_redirected)
        if int(current_time) % 60 == 0:
            self._rebroadcast_to_intersections()
    
    def _rebroadcast_to_intersections(self):
        """Re-diffuse l'info de congestion aux intersections uniquement (sans toucher vehicles_redirected)"""
        from communication.fipa_message import FIPAMessage
        from agents.intersection_agent import IntersectionAgent

        incident_center = (
            (self.blocked_road_coords[0][0] + self.blocked_road_coords[1][0]) / 2,
            (self.blocked_road_coords[0][1] + self.blocked_road_coords[1][1]) / 2
        )
        broadcast_radius = 1000.0

        for agent in self.model.schedule.agents:
            if isinstance(agent, IntersectionAgent):
                import math
                distance = math.sqrt(
                    (agent.position[0] - incident_center[0])**2 +
                    (agent.position[1] - incident_center[1])**2
                )
                if distance <= broadcast_radius:
                    message = FIPAMessage(
                        sender="scenario_manager",
                        receiver=agent.unique_id,
                        performative="inform",
                        content={
                            "type": "congestion",
                            "congestion_level": 1.0,
                            "location": incident_center,
                            "reason": "incident",
                            "blocked_road": self.blocked_road_name
                        }
                    )
                    agent.receive_message(message)
                    self.metrics['congestion_messages_sent'] += 1

    def _resolve_incident(self):
        """Résout l'incident : restaure les arêtes bloquées"""
        logger.success(f"✅ INCIDENT RÉSOLU : {self.blocked_road_name}")
        
        self.incident_active = False
        self.incident_resolved = True  # Marquer comme résolu pour éviter de re-déclencher
        
        # Restaurer les arêtes
        network = self.model.road_network
        for node1_id, node2_id in self.blocked_edges:
            if node1_id in network.nodes and node2_id in network.nodes:
                network.add_edge(node1_id, node2_id)
        
        restored_count = len(self.blocked_edges)
        self.blocked_edges.clear()
        
        # Restaurer la couleur normale du Pont De Gaulle dans SUMO-GUI
        if self.model.sumo_connector:
            self.model.sumo_connector.highlight_pont_de_gaulle(highlight=False, rows=6, bridge_col=2)
        
        logger.info(f"   🔧 {restored_count} arêtes restaurées")
    
    def _collect_travel_time_metrics(self, current_time: float):
        """Collecte les métriques de temps de trajet par phase"""
        from agents.vehicle_agent import VehicleAgent
        
        active_vehicles = [
            v for v in self.model.vehicles 
            if isinstance(v, VehicleAgent) and v.active
        ]
        
        if not active_vehicles:
            return
        
        avg_time = sum(v.travel_time for v in active_vehicles) / len(active_vehicles)
        
        if current_time < self.incident_start_time:
            self.metrics['avg_travel_time_before'].append(avg_time)
        elif current_time < self.incident_end_time:
            self.metrics['avg_travel_time_during'].append(avg_time)
        else:
            self.metrics['avg_travel_time_after'].append(avg_time)
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques du scénario d'incident"""
        def safe_avg(lst):
            return sum(lst) / len(lst) if lst else 0.0
        
        return {
            'name': self.name,
            'incident_active': self.incident_active,
            'blocked_edges_count': len(self.blocked_edges),
            'vehicles_redirected': self.metrics['vehicles_redirected'],
            'congestion_messages_sent': self.metrics['congestion_messages_sent'],
            'avg_travel_time_before_incident': safe_avg(self.metrics['avg_travel_time_before']),
            'avg_travel_time_during_incident': safe_avg(self.metrics['avg_travel_time_during']),
            'avg_travel_time_after_incident': safe_avg(self.metrics['avg_travel_time_after'])
        }
