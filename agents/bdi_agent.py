"""
Architecture BDI (Belief-Desire-Intention) de base pour tous les agents
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid


class BeliefType(Enum):
    """Types de croyances possibles"""
    POSITION = "position"
    TRAFFIC_STATE = "traffic_state"
    ROUTE = "route"
    NEIGHBORS = "neighbors"
    CONGESTION = "congestion"
    SPEED = "speed"
    DESTINATION = "destination"


class DesireType(Enum):
    """Types de désirs possibles"""
    REACH_DESTINATION = "reach_destination"
    MINIMIZE_TRAVEL_TIME = "minimize_travel_time"
    OPTIMIZE_FLOW = "optimize_flow"
    AVOID_CONGESTION = "avoid_congestion"
    COORDINATE_WITH_NEIGHBORS = "coordinate_with_neighbors"
    PRIORITIZE_EMERGENCY = "prioritize_emergency"


class IntentionType(Enum):
    """Types d'intentions possibles"""
    MOVE_FORWARD = "move_forward"
    CHANGE_ROUTE = "change_route"
    STOP = "stop"
    CHANGE_LIGHT_TIMING = "change_light_timing"
    BROADCAST_CONGESTION = "broadcast_congestion"
    NEGOTIATE_WITH_NEIGHBOR = "negotiate_with_neighbor"
    ACCELERATE = "accelerate"
    DECELERATE = "decelerate"


@dataclass
class Belief:
    """Représente une croyance d'un agent"""
    type: BeliefType
    value: Any
    confidence: float = 1.0  # Degré de certitude (0-1)
    timestamp: float = 0.0
    source: str = "self"  # Source de l'information
    
    def is_valid(self, current_time: float, validity_duration: float = 10.0) -> bool:
        """Vérifie si la croyance est encore valide"""
        return (current_time - self.timestamp) < validity_duration


@dataclass
class Desire:
    """Représente un désir d'un agent"""
    type: DesireType
    priority: float = 0.5  # Priorité (0-1)
    conditions: Dict[str, Any] = field(default_factory=dict)
    satisfied: bool = False
    
    def evaluate_satisfaction(self, beliefs: Dict[BeliefType, Belief]) -> bool:
        """Évalue si le désir est satisfait basé sur les croyances"""
        # À implémenter dans les sous-classes
        return self.satisfied


@dataclass
class Intention:
    """Représente une intention d'un agent"""
    type: IntentionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: float = 0.5
    status: str = "pending"  # pending, executing, completed, failed
    parent_desire: DesireType = None
    
    def execute(self, agent: 'BDIAgent') -> bool:
        """Exécute l'intention"""
        # À implémenter dans les sous-classes
        return True


class BDIAgent(ABC):
    """
    Classe de base pour tous les agents utilisant l'architecture BDI
    """
    
    def __init__(self, unique_id: str, model: Any):
        self.unique_id = unique_id if unique_id else str(uuid.uuid4())
        self.model = model
        
        # Composants BDI
        self.beliefs: Dict[BeliefType, Belief] = {}
        self.desires: List[Desire] = []
        self.intentions: List[Intention] = []
        
        # État de l'agent
        self.active = True
        self.current_time = 0.0
        
        # Historique pour apprentissage
        self.action_history: List[Dict] = []
        self.message_inbox: List[Any] = []
        self.message_outbox: List[Any] = []
    
    # ============ BELIEF MANAGEMENT ============
    
    def perceive(self):
        """
        Percevoir l'environnement et mettre à jour les croyances
        Doit être implémenté par chaque type d'agent
        """
        pass
    
    def update_belief(self, belief_type: BeliefType, value: Any, 
                     confidence: float = 1.0, source: str = "self"):
        """Ajoute ou met à jour une croyance"""
        self.beliefs[belief_type] = Belief(
            type=belief_type,
            value=value,
            confidence=confidence,
            timestamp=self.current_time,
            source=source
        )
    
    def get_belief(self, belief_type: BeliefType) -> Any:
        """Récupère la valeur d'une croyance"""
        belief = self.beliefs.get(belief_type)
        return belief.value if belief else None
    
    def remove_outdated_beliefs(self, validity_duration: float = 10.0):
        """Supprime les croyances obsolètes"""
        to_remove = []
        for belief_type, belief in self.beliefs.items():
            if not belief.is_valid(self.current_time, validity_duration):
                to_remove.append(belief_type)
        
        for belief_type in to_remove:
            del self.beliefs[belief_type]
    
    # ============ DESIRE MANAGEMENT ============
    
    @abstractmethod
    def generate_desires(self):
        """
        Génère les désirs basés sur les croyances actuelles
        Doit être implémenté par chaque type d'agent
        """
        pass
    
    def add_desire(self, desire: Desire):
        """Ajoute un nouveau désir"""
        if desire not in self.desires:
            self.desires.append(desire)
    
    def remove_desire(self, desire: Desire):
        """Supprime un désir"""
        if desire in self.desires:
            self.desires.remove(desire)
    
    def filter_desires(self):
        """Filtre les désirs conflictuels ou satisfaits"""
        self.desires = [d for d in self.desires if not d.satisfied]
        # Trier par priorité
        self.desires.sort(key=lambda d: d.priority, reverse=True)
    
    # ============ INTENTION MANAGEMENT ============
    
    @abstractmethod
    def deliberate(self) -> List[Intention]:
        """
        Délibère sur les désirs pour créer des intentions
        Doit être implémenté par chaque type d'agent
        """
        pass
    
    def add_intention(self, intention: Intention):
        """Ajoute une nouvelle intention"""
        self.intentions.append(intention)
    
    def execute_intentions(self):
        """Exécute les intentions en cours"""
        for intention in self.intentions:
            if intention.status == "pending":
                intention.status = "executing"
                success = self.execute_intention(intention)
                intention.status = "completed" if success else "failed"
                
                # Logger l'action
                self.action_history.append({
                    'time': self.current_time,
                    'intention': intention.type.value,
                    'success': success,
                    'parameters': intention.parameters
                })
        
        # Nettoyer les intentions terminées
        self.intentions = [i for i in self.intentions 
                          if i.status not in ["completed", "failed"]]
    
    @abstractmethod
    def execute_intention(self, intention: Intention) -> bool:
        """
        Exécute une intention spécifique
        Doit être implémenté par chaque type d'agent
        """
        pass
    
    # ============ BDI CYCLE ============
    
    def step(self):
        """
        Un pas de la boucle BDI :
        1. Percevoir (update beliefs)
        2. Générer désirs
        3. Délibérer (créer intentions)
        4. Exécuter intentions
        """
        if not self.active:
            return
        
        # 1. Percevoir
        self.perceive()
        self.remove_outdated_beliefs()
        
        # 2. Générer désirs
        self.generate_desires()
        self.filter_desires()
        
        # 3. Délibérer
        new_intentions = self.deliberate()
        for intention in new_intentions:
            self.add_intention(intention)
        
        # 4. Exécuter
        self.execute_intentions()
        
        # Mettre à jour le temps
        self.current_time += self.model.time_step if hasattr(self.model, 'time_step') else 1
    
    # ============ COMMUNICATION ============
    
    def send_message(self, message: Any):
        """Envoie un message"""
        self.message_outbox.append(message)
    
    def receive_message(self, message: Any):
        """Reçoit un message"""
        self.message_inbox.append(message)
    
    def process_messages(self):
        """Traite les messages reçus et met à jour les croyances"""
        for message in self.message_inbox:
            self.handle_message(message)
        self.message_inbox.clear()
    
    @abstractmethod
    def handle_message(self, message: Any):
        """
        Gère un message reçu
        Doit être implémenté par chaque type d'agent
        """
        pass
    
    # ============ UTILITY METHODS ============
    
    def get_state(self) -> Dict:
        """Retourne l'état complet de l'agent pour logging"""
        return {
            'id': self.unique_id,
            'active': self.active,
            'time': self.current_time,
            'beliefs': {bt.value: b.value for bt, b in self.beliefs.items()},
            'desires': [d.type.value for d in self.desires],
            'intentions': [i.type.value for i in self.intentions]
        }
    
    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.unique_id})"
