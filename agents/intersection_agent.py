"""
Agent Intersection (AI) - Gère un carrefour avec feux de signalisation
"""
from typing import List, Dict, Tuple, Optional
from enum import Enum
import numpy as np
from .bdi_agent import (
    BDIAgent, Belief, Desire, Intention,
    BeliefType, DesireType, IntentionType
)


class TrafficLightState(Enum):
    """États possibles d'un feu de signalisation"""
    RED = "red"
    YELLOW = "yellow"
    GREEN = "green"


class Direction(Enum):
    """Directions des voies"""
    NORTH = "north"
    SOUTH = "south"
    EAST = "east"
    WEST = "west"


class IntersectionAgent(BDIAgent):
    """
    Agent représentant une intersection avec feux de signalisation
    
    Perception:
        - Nombre de véhicules sur chaque voie entrante
        - État des intersections voisines
        - Historique de trafic
    
    Actions:
        - Modifier la durée du feu vert/rouge
        - Coordonner avec les intersections voisines
        - Diffuser des informations de congestion
    
    Objectifs:
        - Maximiser le débit local
        - Minimiser le temps d'attente moyen
        - Créer des "ondes vertes" avec les voisins
    """
    
    def __init__(self, unique_id: str, model, position: Tuple[float, float],
                 directions: List[Direction] = None):
        super().__init__(unique_id, model)
        
        # Position de l'intersection
        self.position = position
        
        # Configuration des voies
        if directions is None:
            directions = [Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
        self.directions = directions
        
        # Paramètres de contrôle (AVANT initialisation des feux)
        self.min_green_time = 15.0  # secondes
        self.max_green_time = 90.0
        self.default_green_time = 30.0
        self.yellow_time = 3.0
        self.congestion_threshold = 10
        
        # État des feux pour chaque direction
        self.traffic_lights: Dict[Direction, TrafficLightState] = {}
        self.light_timers: Dict[Direction, float] = {}
        self.green_durations: Dict[Direction, float] = {}
        
        # Initialiser les feux
        self._initialize_traffic_lights()
        
        # Files d'attente par direction
        self.queues: Dict[Direction, List] = {d: [] for d in directions}
        self.queue_lengths: Dict[Direction, int] = {d: 0 for d in directions}
        
        # Capteurs virtuels
        self.vehicle_counts: Dict[Direction, int] = {d: 0 for d in directions}
        self.waiting_times: Dict[Direction, List[float]] = {d: [] for d in directions}
        
        # Intersections voisines
        self.neighbors: List['IntersectionAgent'] = []
        self.neighbor_states: Dict[str, Dict] = {}  # {neighbor_id: {phase, timer, queues, outflow, timestamp}}

        # Onde verte : offset de phase cible calculé depuis les voisins en amont
        self._green_wave_offset: float = 0.0       # décalage cible en secondes
        self._green_wave_phase: str = None          # phase cible imposée par l'onde verte ("NS" ou "EW")
        self._green_wave_active: bool = False       # True si une onde verte est en cours
        self._green_wave_timer: float = 0.0         # durée restante de l'onde verte forcée
        self._neighbor_sync_interval: float = 10.0 # secondes entre deux diffusions d'état
        
        # Q-Learning pour optimisation
        self.q_table: Dict = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.9
        self.epsilon = 0.1  # exploration vs exploitation
        self.epsilon_decay = 0.995
        self.epsilon_min = 0.01
        
        # Suivi état/action précédents pour mise à jour Q-Learning
        self.previous_state: str = None
        self.previous_action: str = None
        self.previous_total_waiting: float = 0.0
        
        # Statistiques
        self.total_vehicles_processed = 0
        self.total_waiting_time = 0.0
        self.phase_changes = 0
        self.coordination_messages_sent = 0
        
        # Initialiser les croyances
        self._initialize_beliefs()
    
    def _initialize_traffic_lights(self):
        """Initialise l'état des feux (alternance Nord-Sud / Est-Ouest)"""
        # Nord et Sud en vert, Est et Ouest en rouge
        for direction in self.directions:
            if direction in [Direction.NORTH, Direction.SOUTH]:
                self.traffic_lights[direction] = TrafficLightState.GREEN
                self.green_durations[direction] = self.default_green_time
                self.light_timers[direction] = 0.0
            else:
                self.traffic_lights[direction] = TrafficLightState.RED
                self.green_durations[direction] = self.default_green_time
                self.light_timers[direction] = 0.0
    
    def _initialize_beliefs(self):
        """Initialise les croyances de base"""
        self.update_belief(BeliefType.POSITION, self.position)
        self.update_belief(BeliefType.TRAFFIC_STATE, "fluide")
        self.update_belief(BeliefType.NEIGHBORS, [])
    
    # ============ PERCEPTION ============
    
    def perceive(self):
        """Percevoir l'état du trafic à l'intersection"""
        # Compter les véhicules dans chaque direction
        self._count_vehicles()
        
        # Mettre à jour les longueurs de file
        for direction in self.directions:
            self.queue_lengths[direction] = len(self.queues[direction])
        
        # Évaluer le niveau de congestion
        max_queue = max(self.queue_lengths.values()) if self.queue_lengths else 0
        
        if max_queue > self.congestion_threshold * 1.5:
            congestion_level = "fort"
        elif max_queue > self.congestion_threshold:
            congestion_level = "moyen"
        else:
            congestion_level = "faible"
        
        self.update_belief(BeliefType.CONGESTION, {
            'level': congestion_level,
            'max_queue': max_queue,
            'queues': dict(self.queue_lengths)
        })
        
        # Mettre à jour l'état des feux
        self.update_belief(BeliefType.TRAFFIC_STATE, {
            'lights': {d: s.value for d, s in self.traffic_lights.items()},
            'timers': dict(self.light_timers)
        })
        
        # Traiter les messages des voisins
        self.process_messages()
    
    def _count_vehicles(self):
        """Compte les véhicules en attente dans chaque direction"""
        # Réinitialiser les compteurs
        for direction in self.directions:
            self.vehicle_counts[direction] = 0
            self.queues[direction].clear()
        
        # Parcourir tous les véhicules
        for agent in self.model.schedule.agents:
            from .vehicle_agent import VehicleAgent
            if isinstance(agent, VehicleAgent):
                # Vérifier si le véhicule est proche de cette intersection
                distance = self._calculate_distance(self.position, agent.position)
                
                if distance < 50.0:  # Rayon de détection de 50m
                    # Déterminer la direction d'approche
                    direction = self._get_approach_direction(agent.position)
                    if direction:
                        self.vehicle_counts[direction] += 1
                        self.queues[direction].append(agent)
    
    def _get_approach_direction(self, vehicle_pos: Tuple[float, float]) -> Optional[Direction]:
        """Détermine de quelle direction arrive un véhicule"""
        dx = vehicle_pos[0] - self.position[0]
        dy = vehicle_pos[1] - self.position[1]
        
        # Déterminer la direction dominante
        if abs(dx) > abs(dy):
            return Direction.EAST if dx > 0 else Direction.WEST
        else:
            return Direction.NORTH if dy > 0 else Direction.SOUTH
    
    # ============ DESIRE GENERATION ============
    
    def generate_desires(self):
        """Génère les désirs basés sur l'état du trafic"""
        self.desires.clear()
        
        # Désir principal : optimiser le flux
        self.add_desire(Desire(
            type=DesireType.OPTIMIZE_FLOW,
            priority=1.0
        ))
        
        # Si congestion détectée
        congestion_info = self.get_belief(BeliefType.CONGESTION)
        if congestion_info and congestion_info.get('level') in ["moyen", "fort"]:
            self.add_desire(Desire(
                type=DesireType.AVOID_CONGESTION,
                priority=0.9
            ))
        
        # Désir de coordination avec voisins
        if self.neighbors:
            self.add_desire(Desire(
                type=DesireType.COORDINATE_WITH_NEIGHBORS,
                priority=0.7
            ))
    
    # ============ DELIBERATION ============
    
    def deliberate(self) -> List[Intention]:
        """Délibère sur les actions à prendre"""
        new_intentions = []
        
        # Mettre à jour les timers des feux
        time_step = self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        for direction in self.directions:
            self.light_timers[direction] += time_step
        
        # Vérifier s'il faut changer de phase
        if self._should_change_phase():
            new_intentions.append(Intention(
                type=IntentionType.CHANGE_LIGHT_TIMING,
                priority=1.0,
                parent_desire=DesireType.OPTIMIZE_FLOW
            ))
        
        # Si congestion, diffuser l'information
        congestion_info = self.get_belief(BeliefType.CONGESTION)
        if congestion_info and congestion_info['level'] == "fort":
            new_intentions.append(Intention(
                type=IntentionType.BROADCAST_CONGESTION,
                priority=0.8,
                parameters={'congestion_level': 0.8, 'location': self.position}
            ))
        
        # Diffuser l'état aux voisins et négocier l'onde verte
        time_step = self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        sync_steps = max(1, int(self._neighbor_sync_interval / time_step))
        if self.neighbors and self.model.current_step % sync_steps == 0:
            new_intentions.append(Intention(
                type=IntentionType.NEGOTIATE_WITH_NEIGHBOR,
                priority=0.75,
                parent_desire=DesireType.COORDINATE_WITH_NEIGHBORS
            ))
        
        return new_intentions
    
    def _should_change_phase(self) -> bool:
        """Détermine s'il faut changer la phase des feux"""
        # Si une onde verte est active, ne pas interrompre la phase imposée
        if self._green_wave_active:
            time_step = self.model.time_step if hasattr(self.model, 'time_step') else 1.0
            self._green_wave_timer -= time_step
            if self._green_wave_timer > 0:
                return False  # Maintenir la phase de l'onde verte
            else:
                self._green_wave_active = False  # Onde verte terminée

        # Utiliser Q-Learning ou heuristique Max-Pressure
        if hasattr(self.model, 'use_q_learning') and self.model.use_q_learning:
            return self._q_learning_decision()
        else:
            return self._max_pressure_decision()
    
    def _q_learning_decision(self) -> bool:
        """Décision basée sur Q-Learning avec mise à jour Bellman"""
        # Respecter min_green_time avant tout changement (comme _max_pressure_decision)
        current_green_timer = 0.0
        for direction in self.directions:
            if self.traffic_lights[direction] == TrafficLightState.GREEN:
                current_green_timer = max(current_green_timer, self.light_timers[direction])
        if current_green_timer < self.min_green_time:
            return False

        # État actuel
        state = self._get_state_representation()
        
        # Initialiser l'état dans la Q-table si nécessaire
        if state not in self.q_table:
            self.q_table[state] = {'change': 0.0, 'keep': 0.0}
        
        # Mise à jour Q-table basée sur l'état/action précédents (Bellman)
        if self.previous_state is not None and self.previous_action is not None:
            reward = self._compute_reward()
            self._update_q_table(self.previous_state, self.previous_action, reward, state)
        
        # Exploration vs Exploitation (epsilon-greedy)
        if np.random.random() < self.epsilon:
            # Exploration : action aléatoire
            action = 'change' if np.random.random() < 0.5 else 'keep'
        else:
            # Exploitation : meilleure action
            q_values = self.q_table[state]
            action = 'change' if q_values['change'] > q_values['keep'] else 'keep'
        
        # Sauvegarder l'état/action pour la prochaine mise à jour
        self.previous_state = state
        self.previous_action = action
        self.previous_total_waiting = sum(self.queue_lengths.values())
        
        # Décroissance de epsilon
        self.epsilon = max(self.epsilon * self.epsilon_decay, self.epsilon_min)
        
        return action == 'change'
    
    def _compute_reward(self) -> float:
        """
        Calcule la récompense pour l'apprentissage par renforcement.
        Récompense positive si le temps d'attente diminue, négative sinon.
        """
        current_total_waiting = sum(self.queue_lengths.values())
        
        # Récompense basée sur la réduction des files d'attente
        waiting_diff = self.previous_total_waiting - current_total_waiting
        
        # Pénalité pour les files très longues
        max_queue = max(self.queue_lengths.values()) if self.queue_lengths else 0
        congestion_penalty = -0.5 * max(0, max_queue - self.congestion_threshold)
        
        # Bonus pour un débit élevé (véhicules traités)
        throughput_bonus = 0.1 * self.total_vehicles_processed
        
        reward = waiting_diff + congestion_penalty + throughput_bonus
        return reward
    
    def _update_q_table(self, state: str, action: str, reward: float, next_state: str):
        """
        Met à jour la Q-table avec l'équation de Bellman :
        Q(s,a) = Q(s,a) + α * [R + γ * max(Q(s',a')) - Q(s,a)]
        """
        # Initialiser le nouvel état si nécessaire
        if next_state not in self.q_table:
            self.q_table[next_state] = {'change': 0.0, 'keep': 0.0}
        
        # Valeur Q actuelle
        current_q = self.q_table[state][action]
        
        # Meilleure valeur Q pour l'état suivant
        max_next_q = max(self.q_table[next_state].values())
        
        # Équation de Bellman
        new_q = current_q + self.learning_rate * (reward + self.discount_factor * max_next_q - current_q)
        
        # Mise à jour
        self.q_table[state][action] = new_q
    
    def _max_pressure_decision(self) -> bool:
        """
        Décision basée sur l'algorithme Max-Pressure complet.
        
        Max-Pressure sélectionne la phase qui maximise la pression totale :
        Pression(phase) = Σ(queue_in - queue_out) pour toutes les directions de la phase
        
        Référence : Varaiya, P. (2013). Max pressure control of a network of signalized intersections.
        """
        # Vérifier que le feu vert actuel a duré au moins min_green_time
        current_green_timer = 0.0
        for direction in self.directions:
            if self.traffic_lights[direction] == TrafficLightState.GREEN:
                current_green_timer = max(current_green_timer, self.light_timers[direction])
        
        if current_green_timer < self.min_green_time:
            return False  # Ne jamais changer avant la durée minimum
        
        # Définir les phases possibles (groupes de directions compatibles)
        ns_directions = [d for d in self.directions if d in (Direction.NORTH, Direction.SOUTH)]
        ew_directions = [d for d in self.directions if d in (Direction.EAST, Direction.WEST)]
        
        phases = {
            'NS': ns_directions,
            'EW': ew_directions
        }
        
        # Calculer la pression pour chaque phase
        phase_pressures = {}
        for phase_name, phase_directions in phases.items():
            total_pressure = 0.0
            
            for direction in phase_directions:
                # Queue entrante (véhicules en attente)
                queue_in = self.queue_lengths.get(direction, 0)
                
                # Queue sortante (estimation basée sur les voisins en aval)
                queue_out = self._estimate_downstream_queue(direction)
                
                # Pression = différence entre entrée et sortie
                pressure = queue_in - queue_out
                total_pressure += pressure
            
            phase_pressures[phase_name] = total_pressure
        
        # Identifier la phase actuelle
        current_phase = self._get_current_phase()
        
        # Identifier la phase avec la pression maximale
        max_pressure_phase = max(phase_pressures, key=phase_pressures.get)
        max_pressure_value = phase_pressures[max_pressure_phase]
        current_pressure_value = phase_pressures[current_phase]
        
        # Décision : changer si la phase alternative a une pression significativement plus élevée
        pressure_threshold = 5.0  # Seuil de différence pour justifier un changement
        
        if max_pressure_phase != current_phase:
            # Changer si la pression de l'autre phase est suffisamment plus élevée
            if max_pressure_value - current_pressure_value > pressure_threshold:
                return True
        
        # Si le feu vert actuel dépasse la durée maximale, forcer le changement
        if current_green_timer > self.max_green_time:
            return True
        
        # Si le feu vert actuel dépasse la durée prévue et la pression est faible, changer
        if (current_green_timer > self.green_durations.get(ns_directions[0] if current_phase == 'NS' else ew_directions[0], self.default_green_time) and
            current_pressure_value < 2.0):
            return True
        
        return False
    
    def _estimate_downstream_queue(self, direction: Direction) -> float:
        """
        Estime la file d'attente en aval pour une direction donnée.
        Utilisé par Max-Pressure pour calculer la pression.
        
        Returns:
            Estimation du nombre de véhicules en aval (0-10)
        """
        # Si on a des informations des voisins, les utiliser
        for neighbor_id, state in self.neighbor_states.items():
            # Vérifier si ce voisin est dans la direction de sortie
            neighbor_queues = state.get('queue_lengths', {})
            
            # Approximation : utiliser la queue moyenne du voisin
            if neighbor_queues:
                avg_neighbor_queue = sum(neighbor_queues.values()) / len(neighbor_queues)
                return min(avg_neighbor_queue, 10.0)
        
        # Sinon, estimation par défaut basée sur l'état du feu
        if self.traffic_lights.get(direction) == TrafficLightState.GREEN:
            # Si le feu est vert, on suppose que les véhicules partent (queue faible en aval)
            return 2.0
        else:
            # Si le feu est rouge, estimation neutre
            return 5.0
    
    def _get_state_representation(self) -> str:
        """Représentation de l'état pour Q-Learning"""
        # Simplification : état = (queue_NS, queue_EW, current_phase)
        ns_queue = sum(self.queue_lengths.get(d, 0) for d in [Direction.NORTH, Direction.SOUTH])
        ew_queue = sum(self.queue_lengths.get(d, 0) for d in [Direction.EAST, Direction.WEST])
        
        current_phase = "NS" if self.traffic_lights.get(Direction.NORTH) == TrafficLightState.GREEN else "EW"
        
        # Discrétiser les queues
        ns_discrete = min(ns_queue // 3, 5)  # 0-5
        ew_discrete = min(ew_queue // 3, 5)
        
        return f"{ns_discrete}_{ew_discrete}_{current_phase}"
    
    # ============ INTENTION EXECUTION ============
    
    def execute_intention(self, intention: Intention) -> bool:
        """Exécute une intention spécifique"""
        try:
            if intention.type == IntentionType.CHANGE_LIGHT_TIMING:
                return self._change_traffic_light_phase()
            
            elif intention.type == IntentionType.BROADCAST_CONGESTION:
                congestion_level = intention.parameters.get('congestion_level', 0.5)
                location = intention.parameters.get('location', self.position)
                return self._broadcast_congestion_info(congestion_level, location)
            
            elif intention.type == IntentionType.NEGOTIATE_WITH_NEIGHBOR:
                return self._broadcast_state_to_neighbors()
            
            return False
        
        except Exception as e:
            print(f"Erreur lors de l'exécution de l'intention {intention.type}: {e}")
            return False
    
    def _change_traffic_light_phase(self) -> bool:
        """Change la phase des feux de signalisation.
        Si une onde verte a mémorisé une phase cible, elle est appliquée
        en priorité (tant que min_green_time est respecté).
        """
        # Déterminer quelle phase est actuellement verte
        current_green_directions = [
            d for d in self.directions
            if self.traffic_lights[d] == TrafficLightState.GREEN
        ]

        if not current_green_directions:
            return False

        # --- Sélectionner la prochaine phase ---
        # Par défaut : inverser la phase actuelle
        current_phase = self._get_current_phase()
        next_phase = "EW" if current_phase == "NS" else "NS"

        # Si une onde verte a mémorisé une phase cible, l'utiliser
        if self._green_wave_phase and not self._green_wave_active:
            next_phase = self._green_wave_phase
            self._green_wave_phase = None   # consommer l'offset
            self._green_wave_offset = 0.0

        # Déterminer les groupes de directions
        ns_group = [d for d in self.directions if d in (Direction.NORTH, Direction.SOUTH)]
        ew_group = [d for d in self.directions if d in (Direction.EAST, Direction.WEST)]
        new_green_group = ns_group if next_phase == "NS" else ew_group
        new_red_group   = ew_group if next_phase == "NS" else ns_group

        # Appliquer la transition
        for direction in new_red_group:
            self.traffic_lights[direction] = TrafficLightState.RED
            self.light_timers[direction] = 0.0

        for direction in new_green_group:
            self.traffic_lights[direction] = TrafficLightState.GREEN
            self.light_timers[direction] = 0.0
            # Adapter la durée du vert selon la queue et le flux prédit des voisins
            queue_length = self.queue_lengths.get(direction, 0)
            # Bonus si un flux entrant est prédit depuis un voisin
            neighbor_bonus = 0.0
            for state in self.neighbor_states.values():
                if state.get('phase') == next_phase:
                    neighbor_bonus = min(state.get('outflow_estimate', 0.0) * 2.0, 20.0)
                    break
            self.green_durations[direction] = min(
                self.min_green_time + queue_length * 2 + neighbor_bonus,
                self.max_green_time
            )

        self.phase_changes += 1
        return True
    
    def _broadcast_congestion_info(self, congestion_level: float, location: Tuple) -> bool:
        """
        Diffuse l'information de congestion aux véhicules à proximité.
        """
        from communication.fipa_message import FIPAMessage
        
        message = FIPAMessage(
            sender=self.unique_id,
            receiver="broadcast",
            performative="INFORM",
            content={
                "type": "congestion",
                "congestion_level": congestion_level,
                "location": location
            }
        )
        
        # Envoyer aux véhicules dans un rayon
        broadcast_radius = 500.0  # mètres
        
        try:
            from .vehicle_agent import VehicleAgent
            for agent in self.model.schedule.agents:
                if isinstance(agent, VehicleAgent) and agent.active:
                    try:
                        distance = self._calculate_distance(self.position, agent.position)
                        if distance <= broadcast_radius:
                            agent.receive_message(message)
                    except:
                        # Ignorer les agents avec erreur
                        continue
        except:
            # En cas d'erreur globale, continuer
            pass
        
        return True
    
    def _broadcast_state_to_neighbors(self) -> bool:
        """
        Diffuse l'état complet de cette intersection à tous ses voisins.
        Chaque voisin utilisera ces informations pour :
          - Anticiper le flux entrant (véhicules libérés par ce feu)
          - Calculer un offset de synchronisation pour créer une onde verte
          - Adapter la durée de leur phase verte
        """
        from communication.fipa_message import FIPAMessage

        current_phase = self._get_current_phase()
        phase_timer   = self._get_phase_timer()
        outflow       = self._estimate_outflow()

        state_content = {
            "type": "neighbor_state",
            "phase": current_phase,
            "phase_timer_remaining": phase_timer,
            "queue_lengths": {d.value: l for d, l in self.queue_lengths.items()},
            "outflow_estimate": outflow,
            "position": self.position,
            "timestamp": self.current_time,
        }

        for neighbor in self.neighbors:
            message = FIPAMessage(
                sender=self.unique_id,
                receiver=neighbor.unique_id,
                performative="INFORM",
                content=state_content,
                protocol="green-wave-coordination"
            )
            neighbor.receive_message(message)
            self.coordination_messages_sent += 1

        # Après diffusion, recalculer notre propre synchronisation
        self._apply_neighbor_coordination()
        return True

    def _estimate_outflow(self) -> float:
        """
        Estime le nombre de véhicules qui vont quitter cette intersection
        dans les prochaines secondes (flux sortant vers les voisins).
        Basé sur la phase verte actuelle et la longueur des files.
        """
        outflow = 0.0
        saturation_flow = 1800.0  # véhicules/heure par voie (valeur standard)
        time_step = self.model.time_step if hasattr(self.model, 'time_step') else 1.0
        vehicles_per_step = saturation_flow / 3600.0 * time_step

        for direction in self.directions:
            if self.traffic_lights.get(direction) == TrafficLightState.GREEN:
                queue = self.queue_lengths.get(direction, 0)
                remaining = self._get_phase_timer()
                outflow += min(queue, vehicles_per_step * remaining)
        return outflow

    def _apply_neighbor_coordination(self):
        """
        Analyse les états reçus des voisins pour :
        1. Détecter un flux entrant imminent (voisin en amont libère des véhicules)
        2. Déclencher une onde verte en anticipant la phase appropriée
        3. Adapter la durée du vert pour absorber le flux prédit
        """
        if not self.neighbor_states:
            return

        current_time = self.current_time
        max_stale_age = 30.0  # ignorer les états vieux de plus de 30s

        best_incoming_flow = 0.0
        best_phase_to_match = None
        best_offset = 0.0

        for neighbor_id, state in self.neighbor_states.items():
            # Ignorer les états trop anciens
            age = current_time - state.get('timestamp', current_time)
            if age > max_stale_age:
                continue

            neighbor_phase    = state.get('phase')
            timer_remaining   = state.get('phase_timer_remaining', 0.0)
            outflow           = state.get('outflow_estimate', 0.0)
            neighbor_pos      = state.get('position')

            if not neighbor_pos or outflow <= 0:
                continue

            # Calculer le temps de propagation du flux (distance / vitesse moyenne)
            distance = self._calculate_distance(self.position, neighbor_pos)
            avg_speed = 8.33  # ~30 km/h en zone urbaine (m/s)
            travel_time = distance / avg_speed if avg_speed > 0 else 0.0

            # Le flux arrivera dans `travel_time` secondes
            # Si le voisin libère des véhicules dans `timer_remaining` secondes,
            # ils arriveront ici dans `timer_remaining + travel_time` secondes
            arrival_in = timer_remaining + travel_time

            # Déterminer quelle phase ici correspond au flux entrant
            # (le flux sortant du voisin arrive dans la direction opposée)
            incoming_phase = neighbor_phase  # NS reste NS, EW reste EW sur un axe

            if outflow > best_incoming_flow:
                best_incoming_flow = outflow
                best_phase_to_match = incoming_phase
                best_offset = arrival_in

        # Si un flux significatif est prédit, préparer l'onde verte
        if best_phase_to_match and best_incoming_flow >= 2.0:
            self._schedule_green_wave(best_phase_to_match, best_offset, best_incoming_flow)

    def _schedule_green_wave(self, target_phase: str, offset: float, expected_flow: float):
        """
        Programme une onde verte : dans `offset` secondes, passer en phase `target_phase`
        pour accueillir le flux entrant prédit depuis un voisin en amont.

        Args:
            target_phase: "NS" ou "EW" — la phase à activer
            offset: délai en secondes avant l'arrivée du flux
            expected_flow: nombre de véhicules attendus
        """
        current_phase = self._get_current_phase()

        # Si on est déjà dans la bonne phase, prolonger le vert
        if current_phase == target_phase:
            extra_time = min(expected_flow * 2.0, self.max_green_time)
            for direction in self.directions:
                if self.traffic_lights.get(direction) == TrafficLightState.GREEN:
                    self.green_durations[direction] = min(
                        self.green_durations[direction] + extra_time,
                        self.max_green_time
                    )
            return

        # Si le flux arrive très bientôt (offset < min_green_time), forcer la phase maintenant
        if offset <= self.min_green_time:
            # Vérifier que le feu actuel a duré assez longtemps
            current_green_timer = 0.0
            for direction in self.directions:
                if self.traffic_lights.get(direction) == TrafficLightState.GREEN:
                    current_green_timer = max(current_green_timer, self.light_timers[direction])

            if current_green_timer >= self.min_green_time:
                # Forcer la phase cible et activer l'onde verte
                target_dir = Direction.NORTH if target_phase == "NS" else Direction.EAST
                self._force_green(target_dir)
                self._green_wave_active = True
                self._green_wave_phase  = target_phase
                self._green_wave_timer  = min(expected_flow * 2.0, self.max_green_time)
        else:
            # Mémoriser l'offset pour l'utiliser lors du prochain changement de phase
            self._green_wave_offset = offset
            self._green_wave_phase  = target_phase
    
    def _get_current_phase(self) -> str:
        """Retourne la phase actuelle (NS ou EW)"""
        if self.traffic_lights.get(Direction.NORTH) == TrafficLightState.GREEN:
            return "NS"
        else:
            return "EW"
    
    def _get_phase_timer(self) -> float:
        """Retourne le temps restant de la phase verte actuelle"""
        for direction in self.directions:
            if self.traffic_lights[direction] == TrafficLightState.GREEN:
                remaining = self.green_durations[direction] - self.light_timers[direction]
                return max(remaining, 0.0)
        return 0.0
    
    # ============ COMMUNICATION ============
    
    def handle_message(self, message):
        """Gère les messages reçus"""
        if message.performative in ("INFORM", "inform"):
            msg_type = message.content.get("type", "")
            if msg_type == "neighbor_state":
                # Stocker l'état du voisin pour la coordination
                self.neighbor_states[message.sender] = message.content
                return
            elif msg_type in ("congestion", "incident_report"):
                # Normaliser le contenu pour garantir la clé 'level'
                content = message.content.copy()
                if 'level' not in content:
                    raw = content.get('congestion_level', 0.0)
                    if raw >= 0.8:
                        content['level'] = 'fort'
                    elif raw >= 0.5:
                        content['level'] = 'moyen'
                    else:
                        content['level'] = 'faible'
                self.update_belief(BeliefType.CONGESTION, content)
                return

        if message.performative == "PROPOSE":
            # Proposition de coordination (legacy)
            if message.content.get("type") == "green_wave_coordination":
                self._handle_green_wave_proposal(message)

        elif message.performative == "QUERY":
            # Requête d'information
            self._handle_query(message)
        
        elif message.performative == "request":
            # Contract Net Protocol : appel d'offres ou requête
            if message.content.get("type") == "call_for_proposals":
                self._handle_cfp(message)
            elif message.content.get("type") == "emergency_priority":
                self._handle_emergency_priority(message)
        
        elif message.performative == "accept-proposal":
            # CNP : notre proposition a été acceptée
            self._execute_cnp_task(message)
        
        elif message.performative == "reject-proposal":
            # CNP : notre proposition a été rejetée, rien à faire
            pass
    
    def _handle_green_wave_proposal(self, message):
        """
        Gère une proposition d'onde verte (legacy PROPOSE).
        Redirige vers le nouveau mécanisme de coordination basé sur INFORM.
        """
        # Convertir en format neighbor_state et traiter
        state = {
            "type": "neighbor_state",
            "phase": message.content.get("my_phase"),
            "phase_timer_remaining": message.content.get("my_timer", 0.0),
            "queue_lengths": {},
            "outflow_estimate": 0.0,
            "position": None,
            "timestamp": self.current_time,
        }
        self.neighbor_states[message.sender] = state
    
    def _handle_query(self, message):
        """Répond à une requête d'information"""
        from communication.fipa_message import FIPAMessage
        
        query_type = message.content.get("query_type", "status")
        
        if query_type == "congestion_status":
            congestion_info = self.get_belief(BeliefType.CONGESTION)
            response_content = {
                "type": "congestion_status",
                "congestion": congestion_info if congestion_info else {"level": "faible"},
                "queue_lengths": {d.value: l for d, l in self.queue_lengths.items()},
                "current_phase": self._get_current_phase()
            }
        elif query_type == "light_status":
            response_content = {
                "type": "light_status",
                "lights": {d.value: s.value for d, s in self.traffic_lights.items()},
                "phase_timer": self._get_phase_timer()
            }
        else:
            response_content = {
                "type": "general_status",
                "position": self.position,
                "vehicles_processed": self.total_vehicles_processed
            }
        
        response = FIPAMessage(
            sender=self.unique_id,
            receiver=message.sender,
            performative="INFORM",
            content=response_content,
            reply_to=message.message_id
        )
        
        sender_agent = self.model.get_agent_by_id(message.sender)
        if sender_agent:
            sender_agent.receive_message(response)
    
    def _handle_cfp(self, message):
        """
        Gère un appel d'offres du Contract Net Protocol.
        L'intersection évalue si elle peut prendre en charge la délégation
        de priorité et envoie une proposition.
        """
        from communication.fipa_message import FIPAMessage, CommunicationProtocol
        
        task = message.content.get("task", "priority_delegation")
        target_direction = message.content.get("direction")
        
        # Évaluer la capacité à prendre en charge la tâche
        current_load = sum(self.queue_lengths.values())
        max_capacity = self.congestion_threshold * len(self.directions)
        availability = 1.0 - (current_load / max(max_capacity, 1))
        
        # Proposer si disponibilité suffisante
        if availability > 0.3:
            proposal = CommunicationProtocol.propose_in_cnp(
                contractor_id=self.unique_id,
                manager_id=message.sender,
                proposal_content={
                    "task": task,
                    "availability": availability,
                    "current_load": current_load,
                    "position": self.position
                },
                cfp_message=message
            )
            sender_agent = self.model.get_agent_by_id(message.sender)
            if sender_agent:
                sender_agent.receive_message(proposal)
                self.coordination_messages_sent += 1
    
    def _execute_cnp_task(self, message):
        """
        Exécute une tâche acceptée via le Contract Net Protocol.
        Ajuste les feux pour faciliter le flux dans la direction demandée.
        """
        task = message.content.get("task", "priority_delegation")
        direction_str = message.content.get("priority_direction")
        
        if task == "priority_delegation" and direction_str:
            # Trouver la direction correspondante
            for direction in self.directions:
                if direction.value == direction_str:
                    # Forcer le feu vert dans cette direction
                    self._force_green(direction)
                    break
    
    def _handle_emergency_priority(self, message):
        """
        Gère une demande de priorité d'urgence (ambulance, bus SOTRA).
        Force le feu vert dans la direction du véhicule d'urgence.
        """
        from communication.fipa_message import FIPAMessage
        
        vehicle_position = message.content.get("vehicle_position")
        vehicle_type = message.content.get("vehicle_type", "emergency")
        
        if vehicle_position:
            # Déterminer la direction d'approche du véhicule d'urgence
            approach_dir = self._get_approach_direction(tuple(vehicle_position))
            
            if approach_dir:
                # Forcer le feu vert dans cette direction
                self._force_green(approach_dir)
                
                # Confirmer la prise en charge
                response = FIPAMessage(
                    sender=self.unique_id,
                    receiver=message.sender,
                    performative="INFORM",
                    content={
                        "type": "emergency_acknowledged",
                        "green_direction": approach_dir.value,
                        "intersection": self.unique_id
                    },
                    reply_to=message.message_id
                )
                sender_agent = self.model.get_agent_by_id(message.sender)
                if sender_agent:
                    sender_agent.receive_message(response)
    
    def _force_green(self, target_direction: Direction):
        """
        Force le feu vert dans une direction spécifique.
        Utilisé pour la priorité d'urgence et le CNP.
        Respecte le min_green_time pour éviter les clignotements.
        """
        # Vérifier que le feu actuel a duré assez longtemps
        for direction in self.directions:
            if (self.traffic_lights[direction] == TrafficLightState.GREEN and
                self.light_timers[direction] < self.min_green_time):
                return  # Ne pas forcer si le feu vert actuel est trop récent
        
        # Si la direction demandée est déjà verte, ne rien faire
        if self.traffic_lights.get(target_direction) == TrafficLightState.GREEN:
            return
        
        # Déterminer le groupe de directions (NS ou EW)
        ns_group = [Direction.NORTH, Direction.SOUTH]
        ew_group = [Direction.EAST, Direction.WEST]
        
        if target_direction in ns_group:
            green_group = ns_group
            red_group = ew_group
        else:
            green_group = ew_group
            red_group = ns_group
        
        # Appliquer les changements
        for direction in green_group:
            if direction in self.traffic_lights:
                self.traffic_lights[direction] = TrafficLightState.GREEN
                self.light_timers[direction] = 0.0
        
        for direction in red_group:
            if direction in self.traffic_lights:
                self.traffic_lights[direction] = TrafficLightState.RED
                self.light_timers[direction] = 0.0
        
        self.phase_changes += 1
    
    # ============ UTILITY METHODS ============
    
    def _calculate_distance(self, pos1: Tuple[float, float], 
                           pos2: Tuple[float, float]) -> float:
        """Calcule la distance euclidienne"""
        return np.sqrt((pos1[0] - pos2[0])**2 + (pos1[1] - pos2[1])**2)
    
    def add_neighbor(self, neighbor: 'IntersectionAgent'):
        """Ajoute une intersection voisine"""
        if neighbor not in self.neighbors:
            self.neighbors.append(neighbor)
            self.update_belief(BeliefType.NEIGHBORS, self.neighbors)
    
    def get_statistics(self) -> dict:
        """Retourne les statistiques de l'intersection"""
        avg_waiting_time = 0.0
        total_waiting = sum(len(times) for times in self.waiting_times.values())
        if total_waiting > 0:
            all_times = [t for times in self.waiting_times.values() for t in times]
            avg_waiting_time = sum(all_times) / len(all_times)

        return {
            'id': self.unique_id,
            'position': self.position,
            'total_vehicles_processed': self.total_vehicles_processed,
            'average_waiting_time': avg_waiting_time,
            'phase_changes': self.phase_changes,
            'current_queues': dict(self.queue_lengths),
            'coordination_messages': self.coordination_messages_sent,
            'neighbors_count': len(self.neighbors),
            'green_wave_active': self._green_wave_active,
            'neighbor_states_count': len(self.neighbor_states),
        }
