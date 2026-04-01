"""
Agent Véhicule (AV) - Représente un véhicule autonome dans la simulation
"""
import math
from typing import Tuple, List, Optional
from .bdi_agent import (
    BDIAgent, Belief, Desire, Intention,
    BeliefType, DesireType, IntentionType
)


class VehicleAgent(BDIAgent):
    """
    Agent représentant un véhicule dans le système de trafic
    
    Perception:
        - Position actuelle
        - Destination
        - État du trafic environnant
        - Messages des intersections
    
    Actions:
        - Accélérer / Décélérer
        - Changer d'itinéraire
        - S'arrêter aux feux rouges
    
    Objectifs:
        - Atteindre la destination
        - Minimiser le temps de trajet
        - Éviter les congestions
    """
    
    def __init__(self, unique_id: str, model, position: Tuple[float, float], 
                 destination: Tuple[float, float], max_speed: float = 13.89,
                 vehicle_type: str = "standard"):
        super().__init__(unique_id, model)
        
        # Type de véhicule : "standard", "ambulance", "bus_sotra", "pompier", "police"
        self.vehicle_type = vehicle_type
        
        # Attributs physiques
        self.position = position
        self.origin = position  # Position initiale (immuable)
        self.destination = destination
        self.speed = 0.0
        self.max_speed = max_speed  # m/s (50 km/h par défaut)
        self.acceleration = 2.0  # m/s²
        self.deceleration = 4.0  # m/s²
        
        # Navigation
        self.current_route: List[Tuple[float, float]] = []
        self.current_waypoint_index = 0
        self.route_recalculation_timer = 0.0
        self.route_recalculation_interval = 30.0  # secondes
        
        # État du véhicule
        self.is_stopped = False
        self.waiting_at_intersection = False
        self.stuck_timer = 0.0
        
        # Statistiques
        self.distance_traveled = 0.0
        self.travel_time = 0.0
        self.route_changes = 0
        self.stops_count = 0
        
        # Initialiser les croyances de base
        self._initialize_beliefs()
    
    def _initialize_beliefs(self):
        """Initialise les croyances de base du véhicule"""
        self.update_belief(BeliefType.POSITION, self.position)
        self.update_belief(BeliefType.DESTINATION, self.destination)
        self.update_belief(BeliefType.SPEED, self.speed)
        self.update_belief(BeliefType.ROUTE, self.current_route)
    
    # ============ PERCEPTION ============
    
    def perceive(self):
        """Percevoir l'environnement"""
        # Mettre à jour la position et les croyances stables
        self.update_belief(BeliefType.POSITION, self.position)
        self.update_belief(BeliefType.SPEED, self.speed)
        self.update_belief(BeliefType.DESTINATION, self.destination)
        self.update_belief(BeliefType.ROUTE, self.current_route)
        
        # Percevoir le trafic environnant
        nearby_vehicles = self._get_nearby_vehicles()
        self.update_belief(BeliefType.NEIGHBORS, nearby_vehicles)
        
        # Percevoir l'état du trafic sur la route actuelle
        traffic_state = self._assess_traffic_state()
        self.update_belief(BeliefType.TRAFFIC_STATE, traffic_state)
        
        # Traiter les messages reçus
        self.process_messages()
    
    def _get_nearby_vehicles(self, radius: float = 100.0) -> List['VehicleAgent']:
        """
        Détecte les véhicules à proximité.
        OPTIMISATION: Cache avec mise à jour toutes les 10 secondes pour réduire
        drastiquement le nombre de calculs (au lieu de chaque step).
        """
        # Cache pour éviter de recalculer à chaque step
        if not hasattr(self, '_nearby_cache_time'):
            self._nearby_cache_time = 0
            self._nearby_cache = []
        
        # Mettre à jour le cache seulement toutes les 10 secondes
        cache_interval = 10.0
        if self.current_time - self._nearby_cache_time >= cache_interval:
            nearby = []
            # Parcourir les agents (simplifié pour éviter les bugs)
            try:
                for agent in self.model.schedule.agents:
                    if isinstance(agent, VehicleAgent) and agent != self and agent.active:
                        try:
                            distance = self._calculate_distance(self.position, agent.position)
                            if distance <= radius:
                                nearby.append(agent)
                        except:
                            # Ignorer les agents avec des positions invalides
                            continue
            except:
                # En cas d'erreur, retourner le cache existant
                return self._nearby_cache
            
            self._nearby_cache = nearby
            self._nearby_cache_time = self.current_time
        
        return self._nearby_cache
    
    def _assess_traffic_state(self) -> str:
        """Évalue l'état du trafic (fluide, dense, congestionné)"""
        nearby_vehicles = self.get_belief(BeliefType.NEIGHBORS)
        if nearby_vehicles is None:
            return "fluide"
        
        num_nearby = len(nearby_vehicles)
        if num_nearby > 10:
            return "congestionné"
        elif num_nearby > 5:
            return "dense"
        else:
            return "fluide"
    
    # ============ DESIRE GENERATION ============
    
    def generate_desires(self):
        """Génère les désirs basés sur les croyances"""
        self.desires.clear()
        
        # Désir principal : atteindre la destination
        if not self._is_at_destination():
            self.add_desire(Desire(
                type=DesireType.REACH_DESTINATION,
                priority=1.0
            ))
        
        # Désir : minimiser le temps de trajet
        self.add_desire(Desire(
            type=DesireType.MINIMIZE_TRAVEL_TIME,
            priority=0.8
        ))
        
        # Désir : éviter la congestion
        traffic_state = self.get_belief(BeliefType.TRAFFIC_STATE)
        if traffic_state in ["dense", "congestionné"]:
            self.add_desire(Desire(
                type=DesireType.AVOID_CONGESTION,
                priority=0.7
            ))
    
    def _is_at_destination(self) -> bool:
        """Vérifie si le véhicule est arrivé à destination"""
        distance = self._calculate_distance(self.position, self.destination)
        
        # Si la position est en GPS (degrés), 10.0 degrés représentent des milliers de kilomètres.
        # Un seuil de 10 mètres correspond à environ 0.0001 degré.
        if abs(self.position[0]) < 10.0 and abs(self.position[1]) < 10.0:  # Coordonnées GPS probables (Abidjan est autour de -4, 5)
            return distance < 0.0005  # Environ 50 mètres
        else:
            return distance < 10.0  # Seuil classique pour coordonnées planaires (mètres)
    
    # ============ DELIBERATION ============
    
    def deliberate(self) -> List[Intention]:
        """Délibère sur les désirs pour créer des intentions"""
        new_intentions = []
        
        # Si pas de route, calculer une route
        if not self.current_route:
            new_intentions.append(Intention(
                type=IntentionType.CHANGE_ROUTE,
                priority=1.0,
                parent_desire=DesireType.REACH_DESTINATION
            ))
            return new_intentions
        
        # Si arrivé à destination, arrêter
        if self._is_at_destination():
            new_intentions.append(Intention(
                type=IntentionType.STOP,
                priority=1.0,
                parent_desire=DesireType.REACH_DESTINATION
            ))
            self.active = False
            return new_intentions
        
        # Si congestion détectée et temps pour recalculer la route
        traffic_state = self.get_belief(BeliefType.TRAFFIC_STATE)
        if (traffic_state == "congestionné" and 
            self.route_recalculation_timer >= self.route_recalculation_interval):
            new_intentions.append(Intention(
                type=IntentionType.CHANGE_ROUTE,
                priority=0.7,
                parent_desire=DesireType.AVOID_CONGESTION
            ))
            self.route_recalculation_timer = 0.0
        
        # Intention de mouvement normal
        if not self.waiting_at_intersection:
            # Vérifier s'il y a un véhicule devant
            nearby = self.get_belief(BeliefType.NEIGHBORS)
            if nearby and self._vehicle_ahead():
                new_intentions.append(Intention(
                    type=IntentionType.DECELERATE,
                    priority=0.9,
                    parameters={'target_speed': self.speed * 0.5}
                ))
            else:
                new_intentions.append(Intention(
                    type=IntentionType.MOVE_FORWARD,
                    priority=0.8,
                    parent_desire=DesireType.REACH_DESTINATION
                ))
        
        return new_intentions
    
    def _vehicle_ahead(self, threshold: float = 20.0) -> bool:
        """Vérifie s'il y a un véhicule devant dans la direction du mouvement"""
        nearby = self.get_belief(BeliefType.NEIGHBORS)
        if not nearby:
            return False
        
        # Simplification : vérifie la distance minimale
        for vehicle in nearby:
            distance = self._calculate_distance(self.position, vehicle.position)
            if distance < threshold and vehicle.speed < self.speed:
                return True
        return False
    
    # ============ INTENTION EXECUTION ============
    
    def execute_intention(self, intention: Intention) -> bool:
        """Exécute une intention spécifique"""
        try:
            if intention.type == IntentionType.MOVE_FORWARD:
                return self._move_forward()
            
            elif intention.type == IntentionType.CHANGE_ROUTE:
                return self._recalculate_route()
            
            elif intention.type == IntentionType.STOP:
                return self._stop()
            
            elif intention.type == IntentionType.ACCELERATE:
                target_speed = intention.parameters.get('target_speed', self.max_speed)
                return self._accelerate(target_speed)
            
            elif intention.type == IntentionType.DECELERATE:
                target_speed = intention.parameters.get('target_speed', 0.0)
                return self._decelerate(target_speed)
            
            return False
        
        except Exception as e:
            print(f"Erreur lors de l'exécution de l'intention {intention.type}: {e}")
            return False
    
    def _move_forward(self) -> bool:
        """Déplace le véhicule vers le prochain waypoint"""
        if not self.current_route or self.current_waypoint_index >= len(self.current_route):
            return False
        
        target = self.current_route[self.current_waypoint_index]
        direction = self._get_direction_to(target)
        
        # Calculer la nouvelle position
        time_step = self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        
        # Accélérer progressivement jusqu'à la vitesse max
        if self.speed < self.max_speed:
            self.speed = min(self.speed + self.acceleration * time_step, self.max_speed)
        
        # Déplacer dans la direction du waypoint
        displacement = self.speed * time_step
        new_x = self.position[0] + direction[0] * displacement
        new_y = self.position[1] + direction[1] * displacement
        
        # Mettre à jour la position
        old_position = self.position
        self.position = (new_x, new_y)
        self.distance_traveled += self._calculate_distance(old_position, self.position)
        
        # Vérifier si le waypoint est atteint
        if self._calculate_distance(self.position, target) < 5.0:
            self.current_waypoint_index += 1
        
        return True
    
    def _recalculate_route(self) -> bool:
        """
        Recalcule la route vers la destination.
        Logs détaillés pour tracer les décisions de reroutage.
        """
        from loguru import logger
        
        # Déterminer la raison du reroutage
        traffic_state = self.get_belief(BeliefType.TRAFFIC_STATE)
        congestion_level = traffic_state.get('congestion_level', 0.0) if isinstance(traffic_state, dict) else 0.0
        
        # Raison du reroutage
        reason = "periodic_check"
        if congestion_level > 0.7:
            reason = "high_congestion"
        elif hasattr(self, '_last_message_type'):
            if self._last_message_type == "congestion":
                reason = "congestion_alert"
            elif self._last_message_type == "incident":
                reason = "incident_alert"
        
        # Calculer la route actuelle restante
        old_route_length = len(self.current_route) - self.current_waypoint_index if self.current_route else 0
        
        # Utiliser l'algorithme de routage du modèle
        if hasattr(self.model, 'calculate_route'):
            new_route = self.model.calculate_route(self.position, self.destination)
            if new_route:
                new_route_length = len(new_route)
                
                # Logger le reroutage avec détails
                logger.info(
                    f"🔄 Reroutage véhicule {self.unique_id} ({self.vehicle_type}) | "
                    f"Raison: {reason} | "
                    f"Congestion: {congestion_level:.2f} | "
                    f"Ancienne route: {old_route_length} waypoints | "
                    f"Nouvelle route: {new_route_length} waypoints | "
                    f"Position: ({self.position[0]:.0f}, {self.position[1]:.0f}) | "
                    f"Destination: ({self.destination[0]:.0f}, {self.destination[1]:.0f}) | "
                    f"Changements totaux: {self.route_changes + 1}"
                )
                
                self.current_route = new_route
                self.current_waypoint_index = 0
                self.route_changes += 1
                self.update_belief(BeliefType.ROUTE, self.current_route)
                
                # Enregistrer dans l'historique pour analyse
                if not hasattr(self, 'reroute_history'):
                    self.reroute_history = []
                
                self.reroute_history.append({
                    'time': self.current_time,
                    'reason': reason,
                    'congestion_level': congestion_level,
                    'old_route_length': old_route_length,
                    'new_route_length': new_route_length,
                    'position': self.position,
                    'vehicle_type': self.vehicle_type
                })
                
                return True
            else:
                logger.warning(
                    f"⚠️ Échec reroutage véhicule {self.unique_id} | "
                    f"Raison: {reason} | "
                    f"Aucune route trouvée de ({self.position[0]:.0f}, {self.position[1]:.0f}) "
                    f"vers ({self.destination[0]:.0f}, {self.destination[1]:.0f})"
                )
        
        return False
    
    def _stop(self) -> bool:
        """Arrête le véhicule"""
        self.speed = 0.0
        self.is_stopped = True
        self.stops_count += 1
        return True
    
    def _accelerate(self, target_speed: float) -> bool:
        """Accélère jusqu'à la vitesse cible"""
        time_step = self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        self.speed = min(self.speed + self.acceleration * time_step, 
                        min(target_speed, self.max_speed))
        return True
    
    def _decelerate(self, target_speed: float) -> bool:
        """Décélère jusqu'à la vitesse cible"""
        time_step = self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        self.speed = max(self.speed - self.deceleration * time_step, 
                        max(target_speed, 0.0))
        return True
    
    # ============ COMMUNICATION ============
    
    def handle_message(self, message):
        """Gère les messages reçus des intersections avec logs détaillés"""
        from loguru import logger
        
        if message.performative == "INFORM":
            # Message d'information sur la congestion
            if "congestion" in message.content:
                congestion_level = message.content.get("congestion_level", 0)
                location = message.content.get("location")
                reason = message.content.get("reason", "")
                msg_type = message.content.get("type", "congestion")
                
                # Logger le message reçu
                logger.debug(
                    f"📨 Message reçu par véhicule {self.unique_id} ({self.vehicle_type}) | "
                    f"Type: {msg_type} | "
                    f"Émetteur: {message.sender} | "
                    f"Congestion: {congestion_level:.2f} | "
                    f"Raison: {reason} | "
                    f"Position véhicule: ({self.position[0]:.0f}, {self.position[1]:.0f})"
                )
                
                # Stocker le type de message pour le reroutage
                self._last_message_type = msg_type
                
                # Mettre à jour les croyances
                self.update_belief(
                    BeliefType.CONGESTION,
                    {"level": congestion_level, "location": location, "reason": reason},
                    source=message.sender
                )
                
                # Si forte congestion ou incident, recalculer IMMÉDIATEMENT
                if congestion_level > 0.7 or reason == "incident":
                    # Forcer le recalcul immédiat au lieu d'attendre le timer
                    if self.active and self.route and len(self.route) > 0:
                        self._recalculate_route()
                        logger.debug(f"🔄 {self.unique_id} recalcule sa route (incident/congestion détecté)")
                    else:
                        # Si pas encore de route, déclencher le timer
                        self.route_recalculation_timer = self.route_recalculation_interval
    
    # ============ UTILITY METHODS ============
    
    def _calculate_distance(self, pos1: Tuple[float, float], 
                           pos2: Tuple[float, float]) -> float:
        """Calcule la distance euclidienne entre deux positions"""
        return math.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def _get_direction_to(self, target: Tuple[float, float]) -> Tuple[float, float]:
        """Retourne le vecteur unitaire de direction vers la cible"""
        dx = target[0] - self.position[0]
        dy = target[1] - self.position[1]
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance == 0:
            return (0, 0)
        
        return (dx / distance, dy / distance)
    
    def get_statistics(self) -> dict:
        """Retourne les statistiques du véhicule"""
        return {
            'id': self.unique_id,
            'vehicle_type': self.vehicle_type,
            'distance_traveled': self.distance_traveled,
            'travel_time': self.travel_time,
            'route_changes': self.route_changes,
            'stops_count': self.stops_count,
            'average_speed': self.distance_traveled / max(self.travel_time, 1),
            'reached_destination': self._is_at_destination()
        }
    
    def step(self):
        """Étape de simulation du véhicule"""
        super().step()
        
        # Incrémenter les timers
        self.travel_time += self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        self.route_recalculation_timer += self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        
        # Détecter si le véhicule est bloqué
        if self.speed < 0.1 and not self.is_stopped:
            self.stuck_timer += self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        else:
            self.stuck_timer = 0.0
