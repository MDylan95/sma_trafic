"""
Implémentation du protocole FIPA-ACL pour la communication entre agents
FIPA = Foundation for Intelligent Physical Agents
ACL = Agent Communication Language
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from enum import Enum
import time


class Performative(Enum):
    """
    Performatives FIPA-ACL standard
    Définit l'intention communicative du message
    """
    # Transfert d'information
    INFORM = "inform"  # Informer d'un fait
    QUERY_IF = "query-if"  # Demander si quelque chose est vrai
    QUERY_REF = "query-ref"  # Demander une référence
    
    # Négociation
    PROPOSE = "propose"  # Proposer une action
    ACCEPT_PROPOSAL = "accept-proposal"  # Accepter une proposition
    REJECT_PROPOSAL = "reject-proposal"  # Rejeter une proposition
    
    # Actions
    REQUEST = "request"  # Demander une action
    AGREE = "agree"  # Accepter de faire une action
    REFUSE = "refuse"  # Refuser de faire une action
    
    # Résultats
    FAILURE = "failure"  # Échec d'une action
    CONFIRM = "confirm"  # Confirmer un fait
    DISCONFIRM = "disconfirm"  # Infirmer un fait
    
    # Généraux
    NOT_UNDERSTOOD = "not-understood"  # Message non compris
    CANCEL = "cancel"  # Annuler une action
    
    # Spécifiques au projet
    INFORM_CONGESTION = "inform-congestion"  # Informer d'une congestion
    REQUEST_ROUTE = "request-route"  # Demander un itinéraire
    COORDINATE = "coordinate"  # Coordonner des actions


@dataclass
class FIPAMessage:
    """
    Message FIPA-ACL
    
    Structure:
        - sender: ID de l'agent émetteur
        - receiver: ID de l'agent récepteur (ou "broadcast")
        - performative: Type de message (intention communicative)
        - content: Contenu du message (dictionnaire)
        - language: Langage du contenu (par défaut: JSON)
        - ontology: Ontologie utilisée (optionnel)
        - protocol: Protocole d'interaction (optionnel)
        - conversation_id: ID de la conversation (pour suivre les échanges)
        - reply_to: Message auquel celui-ci répond
        - reply_by: Date limite de réponse
    """
    sender: str
    receiver: str
    performative: str
    content: Dict[str, Any]
    
    # Paramètres optionnels
    language: str = "JSON"
    ontology: Optional[str] = None
    protocol: Optional[str] = None
    conversation_id: Optional[str] = None
    reply_to: Optional[str] = None
    reply_by: Optional[float] = None
    
    # Métadonnées
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: f"msg_{int(time.time() * 1000)}")
    
    def __post_init__(self):
        """Validation après initialisation"""
        # Convertir le performative en enum si c'est une string
        if isinstance(self.performative, str):
            try:
                self.performative = Performative(self.performative.lower()).value
            except ValueError:
                # Garder la valeur si ce n'est pas un performative standard
                pass
    
    def to_dict(self) -> Dict:
        """Convertit le message en dictionnaire"""
        return {
            'sender': self.sender,
            'receiver': self.receiver,
            'performative': self.performative,
            'content': self.content,
            'language': self.language,
            'ontology': self.ontology,
            'protocol': self.protocol,
            'conversation_id': self.conversation_id,
            'reply_to': self.reply_to,
            'reply_by': self.reply_by,
            'timestamp': self.timestamp,
            'message_id': self.message_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FIPAMessage':
        """Crée un message depuis un dictionnaire"""
        return cls(**data)
    
    def is_broadcast(self) -> bool:
        """Vérifie si c'est un message broadcast"""
        return self.receiver == "broadcast"
    
    def is_reply_to(self, message_id: str) -> bool:
        """Vérifie si ce message est une réponse à un autre"""
        return self.reply_to == message_id
    
    def create_reply(self, performative: str, content: Dict) -> 'FIPAMessage':
        """Crée un message de réponse"""
        return FIPAMessage(
            sender=self.receiver,  # L'ancien destinataire devient l'émetteur
            receiver=self.sender,  # L'ancien émetteur devient le destinataire
            performative=performative,
            content=content,
            conversation_id=self.conversation_id,
            reply_to=self.message_id,
            protocol=self.protocol,
            ontology=self.ontology
        )
    
    def __repr__(self):
        return (f"FIPAMessage(sender={self.sender}, receiver={self.receiver}, "
                f"performative={self.performative}, id={self.message_id})")


class MessageQueue:
    """
    File de messages pour un agent
    Gère l'envoi et la réception de messages
    """
    
    def __init__(self, max_size: int = 1000):
        self.inbox: list[FIPAMessage] = []
        self.outbox: list[FIPAMessage] = []
        self.max_size = max_size
        self.message_count = 0
    
    def add_to_inbox(self, message: FIPAMessage):
        """Ajoute un message à la boîte de réception"""
        if len(self.inbox) < self.max_size:
            self.inbox.append(message)
        else:
            # Si pleine, retirer le plus ancien
            self.inbox.pop(0)
            self.inbox.append(message)
    
    def add_to_outbox(self, message: FIPAMessage):
        """Ajoute un message à la boîte d'envoi"""
        self.outbox.append(message)
        self.message_count += 1
    
    def get_from_inbox(self, performative: Optional[str] = None) -> Optional[FIPAMessage]:
        """Récupère un message de la boîte de réception"""
        if not self.inbox:
            return None
        
        if performative:
            # Chercher un message avec le performative spécifié
            for i, msg in enumerate(self.inbox):
                if msg.performative == performative:
                    return self.inbox.pop(i)
            return None
        else:
            # Retourner le premier message
            return self.inbox.pop(0)
    
    def peek_inbox(self, performative: Optional[str] = None) -> Optional[FIPAMessage]:
        """Regarde un message sans le retirer"""
        if not self.inbox:
            return None
        
        if performative:
            for msg in self.inbox:
                if msg.performative == performative:
                    return msg
            return None
        else:
            return self.inbox[0]
    
    def clear_inbox(self):
        """Vide la boîte de réception"""
        self.inbox.clear()
    
    def clear_outbox(self):
        """Vide la boîte d'envoi"""
        self.outbox.clear()
    
    def get_inbox_size(self) -> int:
        """Retourne le nombre de messages en réception"""
        return len(self.inbox)
    
    def get_outbox_size(self) -> int:
        """Retourne le nombre de messages en envoi"""
        return len(self.outbox)


class CommunicationProtocol:
    """
    Protocoles de communication standard FIPA
    """
    
    @staticmethod
    def request_protocol(initiator_id: str, participant_id: str, 
                        request_content: Dict) -> FIPAMessage:
        """
        Protocole FIPA-Request
        L'initiateur demande au participant d'effectuer une action
        """
        return FIPAMessage(
            sender=initiator_id,
            receiver=participant_id,
            performative=Performative.REQUEST.value,
            content=request_content,
            protocol="fipa-request"
        )
    
    @staticmethod
    def query_protocol(initiator_id: str, participant_id: str,
                      query_content: Dict) -> FIPAMessage:
        """
        Protocole FIPA-Query
        L'initiateur interroge le participant
        """
        return FIPAMessage(
            sender=initiator_id,
            receiver=participant_id,
            performative=Performative.QUERY_REF.value,
            content=query_content,
            protocol="fipa-query"
        )
    
    @staticmethod
    def contract_net_protocol(manager_id: str, content: Dict) -> FIPAMessage:
        """
        Contract Net Protocol (CNP)
        Le manager diffuse un appel d'offres
        """
        return FIPAMessage(
            sender=manager_id,
            receiver="broadcast",
            performative=Performative.REQUEST.value,
            content={
                "type": "call_for_proposals",
                **content
            },
            protocol="fipa-contract-net"
        )
    
    @staticmethod
    def propose_in_cnp(contractor_id: str, manager_id: str, 
                      proposal_content: Dict, cfp_message: FIPAMessage) -> FIPAMessage:
        """
        Proposition dans le cadre du Contract Net Protocol
        """
        return FIPAMessage(
            sender=contractor_id,
            receiver=manager_id,
            performative=Performative.PROPOSE.value,
            content=proposal_content,
            protocol="fipa-contract-net",
            conversation_id=cfp_message.conversation_id,
            reply_to=cfp_message.message_id
        )
    
    @staticmethod
    def inform_congestion(intersection_id: str, congestion_level: float,
                         location: tuple) -> FIPAMessage:
        """
        Message spécifique : informer d'une congestion
        """
        return FIPAMessage(
            sender=intersection_id,
            receiver="broadcast",
            performative=Performative.INFORM.value,
            content={
                "type": "congestion",
                "congestion_level": congestion_level,
                "location": location,
                "timestamp": time.time()
            },
            protocol="traffic-management"
        )
    
    @staticmethod
    def coordinate_green_wave(intersection_id: str, neighbor_id: str,
                             phase_info: Dict) -> FIPAMessage:
        """
        Message spécifique : coordonner une onde verte
        """
        return FIPAMessage(
            sender=intersection_id,
            receiver=neighbor_id,
            performative=Performative.PROPOSE.value,
            content={
                "type": "green_wave_coordination",
                **phase_info
            },
            protocol="green-wave-coordination"
        )


class MessageRouter:
    """
    Routeur de messages pour la simulation
    Distribue les messages entre les agents
    """
    
    def __init__(self, model):
        self.model = model
        self.total_messages_routed = 0
        self.messages_by_type = {}
        self.broadcast_radius = 500.0  # mètres
    
    def route_message(self, message: FIPAMessage):
        """Route un message vers son/ses destinataire(s)"""
        self.total_messages_routed += 1
        
        # Compter par type
        perf = message.performative
        self.messages_by_type[perf] = self.messages_by_type.get(perf, 0) + 1
        
        if message.is_broadcast():
            self._broadcast_message(message)
        else:
            self._unicast_message(message)
    
    def _unicast_message(self, message: FIPAMessage):
        """Envoie un message à un agent spécifique"""
        receiver = self.model.get_agent_by_id(message.receiver)
        if receiver:
            receiver.receive_message(message)
    
    def _broadcast_message(self, message: FIPAMessage):
        """Diffuse un message à tous les agents dans un rayon"""
        # Trouver l'émetteur pour connaître sa position
        sender = self.model.get_agent_by_id(message.sender)
        if not sender or not hasattr(sender, 'position'):
            return
        
        sender_pos = sender.position
        
        # Diffuser aux agents dans le rayon
        for agent in self.model.schedule.agents:
            if agent.unique_id != message.sender and hasattr(agent, 'position'):
                distance = self._calculate_distance(sender_pos, agent.position)
                if distance <= self.broadcast_radius:
                    agent.receive_message(message)
    
    def _calculate_distance(self, pos1: tuple, pos2: tuple) -> float:
        """Calcule la distance euclidienne"""
        import math
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def get_statistics(self) -> Dict:
        """Retourne les statistiques de communication"""
        return {
            'total_messages': self.total_messages_routed,
            'messages_by_type': dict(self.messages_by_type)
        }
