"""
Agent Gestionnaire de Crise (AGC) - Niveau Avancé
Supervise les situations prioritaires : ambulances, bus SOTRA, vagues vertes forcées
"""
from typing import List, Dict, Tuple, Optional
from enum import Enum
import numpy as np
from .bdi_agent import (
    BDIAgent, Belief, Desire, Intention,
    BeliefType, DesireType, IntentionType
)


class EmergencyVehicleType(Enum):
    """Types de véhicules d'urgence"""
    AMBULANCE = "ambulance"
    BUS_SOTRA = "bus_sotra"
    POMPIER = "pompier"
    POLICE = "police"


class CrisisManagerAgent(BDIAgent):
    """
    Agent Gestionnaire de Crise
    
    Rôle:
        - Superviser les situations prioritaires
        - Prioriser le passage des véhicules d'urgence (ambulances, bus SOTRA)
        - Forcer des "vagues vertes" sur un trajet donné
        - Utiliser le Contract Net Protocol pour déléguer la priorité aux intersections
    
    Perception:
        - Véhicules d'urgence actifs et leurs positions
        - État de congestion global
        - Incidents en cours
    
    Actions:
        - Envoyer des demandes de priorité aux intersections (CNP)
        - Forcer une vague verte sur un trajet
        - Coordonner la réponse aux incidents
    """
    
    def __init__(self, unique_id: str, model):
        super().__init__(unique_id, model)
        
        # Véhicules d'urgence actifs
        self.emergency_vehicles: List[Dict] = []
        
        # Trajets de vague verte actifs
        self.active_green_waves: List[Dict] = []
        
        # Incidents en cours
        self.active_incidents: List[Dict] = []
        
        # Historique des interventions
        self.interventions_count = 0
        self.green_waves_created = 0
        
        # Propositions CNP reçues (pour évaluation)
        self.cnp_proposals: Dict[str, List[Dict]] = {}
        
        # Position virtuelle (centre de la zone supervisée)
        self.position = (0, 0)
        
        # Initialiser les croyances
        self._initialize_beliefs()
    
    def _initialize_beliefs(self):
        """Initialise les croyances de base"""
        self.update_belief(BeliefType.POSITION, self.position)
        self.update_belief(BeliefType.TRAFFIC_STATE, "normal")
    
    # ============ PERCEPTION ============
    
    def perceive(self):
        """Percevoir l'état global du système"""
        # Détecter les véhicules d'urgence
        self._detect_emergency_vehicles()
        
        # Évaluer l'état de congestion global
        self._assess_global_congestion()
        
        # Traiter les messages reçus
        self.process_messages()
    
    def _detect_emergency_vehicles(self):
        """Détecte les véhicules d'urgence actifs dans la simulation"""
        self.emergency_vehicles.clear()
        
        from .vehicle_agent import VehicleAgent
        for agent in self.model.schedule.agents:
            if isinstance(agent, VehicleAgent) and agent.active:
                if hasattr(agent, 'vehicle_type') and agent.vehicle_type in [
                    e.value for e in EmergencyVehicleType
                ]:
                    self.emergency_vehicles.append({
                        'id': agent.unique_id,
                        'type': agent.vehicle_type,
                        'position': agent.position,
                        'destination': agent.destination,
                        'route': agent.current_route
                    })
    
    def _assess_global_congestion(self):
        """Évalue le niveau de congestion global"""
        from .intersection_agent import IntersectionAgent
        
        total_queue = 0
        num_intersections = 0
        congested_intersections = []
        
        for agent in self.model.schedule.agents:
            if isinstance(agent, IntersectionAgent):
                num_intersections += 1
                queue_sum = sum(agent.queue_lengths.values())
                total_queue += queue_sum
                
                if queue_sum > agent.congestion_threshold * len(agent.directions):
                    congested_intersections.append({
                        'id': agent.unique_id,
                        'position': agent.position,
                        'queue_total': queue_sum
                    })
        
        avg_queue = total_queue / max(num_intersections, 1)
        
        if avg_queue > 15:
            congestion_state = "critique"
        elif avg_queue > 8:
            congestion_state = "fort"
        elif avg_queue > 4:
            congestion_state = "moyen"
        else:
            congestion_state = "faible"
        
        self.update_belief(BeliefType.CONGESTION, {
            'level': congestion_state,
            'average_queue': avg_queue,
            'congested_intersections': congested_intersections
        })
        self.update_belief(BeliefType.TRAFFIC_STATE, congestion_state)
    
    # ============ DESIRE GENERATION ============
    
    def generate_desires(self):
        """Génère les désirs basés sur les croyances"""
        self.desires.clear()
        
        # Si des véhicules d'urgence sont actifs, priorité absolue
        if self.emergency_vehicles:
            self.add_desire(Desire(
                type=DesireType.PRIORITIZE_EMERGENCY,
                priority=1.0,
                conditions={'emergency_vehicles': len(self.emergency_vehicles)}
            ))
        
        # Si congestion critique, coordonner
        congestion_info = self.get_belief(BeliefType.CONGESTION)
        if congestion_info and congestion_info['level'] in ["fort", "critique"]:
            self.add_desire(Desire(
                type=DesireType.COORDINATE_WITH_NEIGHBORS,
                priority=0.8
            ))
        
        # Optimiser le flux global
        self.add_desire(Desire(
            type=DesireType.OPTIMIZE_FLOW,
            priority=0.5
        ))
    
    # ============ DELIBERATION ============
    
    def deliberate(self) -> List[Intention]:
        """Délibère sur les actions à prendre"""
        new_intentions = []
        
        # Priorité 1 : Gérer les véhicules d'urgence
        for ev in self.emergency_vehicles:
            new_intentions.append(Intention(
                type=IntentionType.BROADCAST_CONGESTION,
                priority=1.0,
                parameters={
                    'action': 'create_green_wave',
                    'vehicle_id': ev['id'],
                    'vehicle_type': ev['type'],
                    'vehicle_position': ev['position'],
                    'vehicle_destination': ev['destination'],
                    'route': ev.get('route', [])
                },
                parent_desire=DesireType.PRIORITIZE_EMERGENCY
            ))
        
        # Priorité 2 : Gérer la congestion via CNP
        congestion_info = self.get_belief(BeliefType.CONGESTION)
        if congestion_info and congestion_info.get('congested_intersections'):
            new_intentions.append(Intention(
                type=IntentionType.NEGOTIATE_WITH_NEIGHBOR,
                priority=0.8,
                parameters={
                    'action': 'delegate_priority',
                    'congested': congestion_info['congested_intersections']
                },
                parent_desire=DesireType.COORDINATE_WITH_NEIGHBORS
            ))
        
        return new_intentions
    
    # ============ INTENTION EXECUTION ============
    
    def execute_intention(self, intention: Intention) -> bool:
        """Exécute une intention spécifique"""
        try:
            action = intention.parameters.get('action', '')
            
            if action == 'create_green_wave':
                return self._create_green_wave(intention.parameters)
            
            elif action == 'delegate_priority':
                return self._delegate_priority_via_cnp(intention.parameters)
            
            return False
        
        except Exception as e:
            print(f"Erreur CrisisManager - intention {intention.type}: {e}")
            return False
    
    def _create_green_wave(self, params: Dict) -> bool:
        """
        Crée une vague verte sur le trajet d'un véhicule d'urgence.
        Envoie des demandes de priorité à toutes les intersections sur le trajet.
        """
        from communication.fipa_message import FIPAMessage
        from .intersection_agent import IntersectionAgent
        
        vehicle_id = params.get('vehicle_id')
        vehicle_type = params.get('vehicle_type')
        vehicle_position = params.get('vehicle_position')
        route = params.get('route', [])
        
        intersections_notified = 0
        
        # Trouver les intersections sur le trajet ou à proximité
        for agent in self.model.schedule.agents:
            if isinstance(agent, IntersectionAgent):
                # Vérifier si l'intersection est proche du trajet
                min_distance = float('inf')
                
                if route:
                    for waypoint in route:
                        dist = np.sqrt(
                            (agent.position[0] - waypoint[0])**2 +
                            (agent.position[1] - waypoint[1])**2
                        )
                        min_distance = min(min_distance, dist)
                else:
                    # Si pas de route, utiliser la distance directe
                    min_distance = np.sqrt(
                        (agent.position[0] - vehicle_position[0])**2 +
                        (agent.position[1] - vehicle_position[1])**2
                    )
                
                # Si l'intersection est sur le trajet (rayon de 300m)
                if min_distance < 300.0:
                    message = FIPAMessage(
                        sender=self.unique_id,
                        receiver=agent.unique_id,
                        performative="request",
                        content={
                            "type": "emergency_priority",
                            "vehicle_id": vehicle_id,
                            "vehicle_type": vehicle_type,
                            "vehicle_position": list(vehicle_position),
                            "priority": "absolute"
                        },
                        protocol="emergency-management"
                    )
                    agent.receive_message(message)
                    intersections_notified += 1
        
        if intersections_notified > 0:
            self.green_waves_created += 1
            self.interventions_count += 1
            
            # Enregistrer la vague verte active
            self.active_green_waves.append({
                'vehicle_id': vehicle_id,
                'vehicle_type': vehicle_type,
                'intersections_notified': intersections_notified,
                'timestamp': self.current_time
            })
            
            return True
        
        return False
    
    def _delegate_priority_via_cnp(self, params: Dict) -> bool:
        """
        Utilise le Contract Net Protocol pour déléguer la gestion
        de la congestion aux intersections les moins chargées.
        """
        from communication.fipa_message import CommunicationProtocol
        from .intersection_agent import IntersectionAgent
        from agents.crisis_manager_agent import FIPAMessageCopy
        
        congested = params.get('congested', [])
        
        for congested_info in congested:
            congested_id = congested_info['id']
            
            # Déterminer la direction la plus congestionnée pour cet agent
            congested_agent = self.model.get_agent_by_id(congested_id)
            if congested_agent and hasattr(congested_agent, 'queue_lengths') and congested_agent.queue_lengths:
                worst_direction = max(congested_agent.queue_lengths, key=congested_agent.queue_lengths.get)
                priority_direction = worst_direction.value if hasattr(worst_direction, 'value') else str(worst_direction)
            else:
                priority_direction = "unknown"
            
            # Créer un appel d'offres (CFP) via le CNP
            cfp = CommunicationProtocol.contract_net_protocol(
                manager_id=self.unique_id,
                content={
                    "task": "priority_delegation",
                    "congested_intersection": congested_id,
                    "congestion_level": congested_info.get('queue_total', 0),
                    "direction": priority_direction
                }
            )
            
            # Envoyer le CFP aux intersections voisines de l'intersection congestionnée
            congested_agent = self.model.get_agent_by_id(congested_id)
            if congested_agent and hasattr(congested_agent, 'neighbors'):
                for neighbor in congested_agent.neighbors:
                    cfp_copy = FIPAMessageCopy(cfp, neighbor.unique_id)
                    neighbor.receive_message(cfp_copy)
            
            self.interventions_count += 1
        
        return True
    
    # ============ COMMUNICATION ============
    
    def handle_message(self, message):
        """Gère les messages reçus"""
        if message.performative == "propose":
            # Réponse à un CFP : évaluer la proposition
            self._evaluate_cnp_proposal(message)
        
        elif message.performative == "inform":
            # Information sur un incident ou un état
            if message.content.get("type") == "incident_report":
                self._handle_incident_report(message)
            elif message.content.get("type") == "emergency_acknowledged":
                pass  # Confirmation reçue
    
    def _evaluate_cnp_proposal(self, message):
        """
        Évalue les propositions reçues dans le cadre du CNP.
        Accepte la meilleure proposition (plus haute disponibilité).
        """
        from communication.fipa_message import FIPAMessage
        
        conversation_id = message.conversation_id or "default"
        
        if conversation_id not in self.cnp_proposals:
            self.cnp_proposals[conversation_id] = []
        
        self.cnp_proposals[conversation_id].append({
            'sender': message.sender,
            'availability': message.content.get('availability', 0),
            'current_load': message.content.get('current_load', 0),
            'message': message
        })
        
        # Évaluer après avoir reçu suffisamment de propositions
        proposals = self.cnp_proposals[conversation_id]
        if len(proposals) >= 2:
            # Sélectionner la meilleure proposition
            best = max(proposals, key=lambda p: p['availability'])
            
            for proposal in proposals:
                if proposal['sender'] == best['sender']:
                    # Accepter
                    accept_msg = FIPAMessage(
                        sender=self.unique_id,
                        receiver=proposal['sender'],
                        performative="accept-proposal",
                        content={
                            "task": "priority_delegation",
                            "priority_direction": "north"
                        },
                        conversation_id=conversation_id
                    )
                else:
                    # Rejeter
                    accept_msg = FIPAMessage(
                        sender=self.unique_id,
                        receiver=proposal['sender'],
                        performative="reject-proposal",
                        content={"reason": "better_proposal_received"},
                        conversation_id=conversation_id
                    )
                
                target = self.model.get_agent_by_id(proposal['sender'])
                if target:
                    target.receive_message(accept_msg)
            
            # Nettoyer
            del self.cnp_proposals[conversation_id]
    
    def _handle_incident_report(self, message):
        """Gère un rapport d'incident"""
        incident = {
            'location': message.content.get('location'),
            'type': message.content.get('incident_type', 'unknown'),
            'severity': message.content.get('severity', 'medium'),
            'reported_by': message.sender,
            'timestamp': self.current_time
        }
        self.active_incidents.append(incident)
    
    # ============ UTILITY METHODS ============
    
    def register_emergency_vehicle(self, vehicle_id: str, vehicle_type: str,
                                    position: Tuple, destination: Tuple,
                                    route: List = None):
        """
        Enregistre manuellement un véhicule d'urgence.
        Appelé par le modèle lors de la création d'un véhicule prioritaire.
        """
        self.emergency_vehicles.append({
            'id': vehicle_id,
            'type': vehicle_type,
            'position': position,
            'destination': destination,
            'route': route or []
        })
    
    def get_statistics(self) -> dict:
        """Retourne les statistiques du gestionnaire de crise"""
        return {
            'id': self.unique_id,
            'interventions_count': self.interventions_count,
            'green_waves_created': self.green_waves_created,
            'active_incidents': len(self.active_incidents),
            'active_emergency_vehicles': len(self.emergency_vehicles)
        }


def FIPAMessageCopy(original_message, new_receiver: str):
    """Crée une copie d'un FIPAMessage avec un nouveau destinataire"""
    from communication.fipa_message import FIPAMessage
    return FIPAMessage(
        sender=original_message.sender,
        receiver=new_receiver,
        performative=original_message.performative,
        content=original_message.content.copy(),
        protocol=original_message.protocol,
        conversation_id=original_message.conversation_id
    )
