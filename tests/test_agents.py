"""
Tests unitaires pour les agents du système
"""
import pytest
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.bdi_agent import BDIAgent, Belief, Desire, Intention, BeliefType, DesireType
from agents.vehicle_agent import VehicleAgent
from agents.intersection_agent import IntersectionAgent
from environment.traffic_model import TrafficModel


class MockModel:
    """Modèle simulé pour les tests"""
    def __init__(self):
        self.time_step = 1.0
        self.current_step = 0
        self.schedule = MockSchedule()

    def get_agent_by_id(self, agent_id: str):
        for agent in self.schedule.agents:
            if agent.unique_id == agent_id:
                return agent
        return None


class MockSchedule:
    """Ordonnanceur simulé"""
    def __init__(self):
        self.agents = []
    
    def add(self, agent):
        self.agents.append(agent)
    
    def remove(self, agent):
        if agent in self.agents:
            self.agents.remove(agent)


class TestBDIAgent:
    """Tests pour la classe de base BDIAgent"""
    
    def test_belief_creation(self):
        """Test la création de croyances"""
        model = MockModel()
        
        class TestAgent(BDIAgent):
            def perceive(self): pass
            def generate_desires(self): pass
            def deliberate(self): return []
            def execute_intention(self, intention): return True
            def handle_message(self, message): pass
        
        agent = TestAgent("test_agent", model)
        
        # Ajouter une croyance
        agent.update_belief(BeliefType.POSITION, (100, 200))
        
        # Vérifier
        assert BeliefType.POSITION in agent.beliefs
        assert agent.get_belief(BeliefType.POSITION) == (100, 200)
    
    def test_belief_validity(self):
        """Test la validité des croyances dans le temps"""
        belief = Belief(
            type=BeliefType.POSITION,
            value=(0, 0),
            timestamp=0.0
        )
        
        # Valide au temps 5
        assert belief.is_valid(5.0, validity_duration=10.0) == True
        
        # Invalide au temps 15
        assert belief.is_valid(15.0, validity_duration=10.0) == False
    
    def test_desire_priority(self):
        """Test la priorisation des désirs"""
        model = MockModel()
        
        class TestAgent(BDIAgent):
            def perceive(self): pass
            def generate_desires(self): pass
            def deliberate(self): return []
            def execute_intention(self, intention): return True
            def handle_message(self, message): pass
        
        agent = TestAgent("test_agent", model)
        
        # Ajouter des désirs avec différentes priorités
        desire1 = Desire(type=DesireType.REACH_DESTINATION, priority=0.5)
        desire2 = Desire(type=DesireType.MINIMIZE_TRAVEL_TIME, priority=0.8)
        desire3 = Desire(type=DesireType.AVOID_CONGESTION, priority=0.3)
        
        agent.add_desire(desire1)
        agent.add_desire(desire2)
        agent.add_desire(desire3)
        
        # Filtrer (trier par priorité)
        agent.filter_desires()
        
        # Vérifier l'ordre
        assert agent.desires[0].priority == 0.8
        assert agent.desires[1].priority == 0.5
        assert agent.desires[2].priority == 0.3


class TestVehicleAgent:
    """Tests pour VehicleAgent"""
    
    def test_vehicle_creation(self):
        """Test la création d'un véhicule"""
        model = MockModel()
        
        vehicle = VehicleAgent(
            unique_id="vehicle_1",
            model=model,
            position=(0, 0),
            destination=(100, 100),
            max_speed=13.89
        )
        
        assert vehicle.unique_id == "vehicle_1"
        assert vehicle.position == (0, 0)
        assert vehicle.destination == (100, 100)
        assert vehicle.speed == 0.0
        assert vehicle.max_speed == 13.89
    
    def test_vehicle_distance_calculation(self):
        """Test le calcul de distance"""
        model = MockModel()
        
        vehicle = VehicleAgent(
            unique_id="vehicle_1",
            model=model,
            position=(0, 0),
            destination=(3, 4)
        )
        
        # Distance euclidienne entre (0,0) et (3,4) = 5
        distance = vehicle._calculate_distance((0, 0), (3, 4))
        assert distance == 5.0
    
    def test_vehicle_arrival(self):
        """Test la détection d'arrivée"""
        model = MockModel()
        
        vehicle = VehicleAgent(
            unique_id="vehicle_1",
            model=model,
            position=(100, 100),
            destination=(105, 105)  # Très proche
        )
        
        # Devrait être considéré comme arrivé
        assert vehicle._is_at_destination() == True
    
    def test_vehicle_direction(self):
        """Test le calcul de direction"""
        model = MockModel()
        
        vehicle = VehicleAgent(
            unique_id="vehicle_1",
            model=model,
            position=(0, 0),
            destination=(10, 0)
        )
        
        direction = vehicle._get_direction_to((10, 0))
        
        # Direction devrait être (1, 0) - vers l'est
        assert abs(direction[0] - 1.0) < 0.001
        assert abs(direction[1] - 0.0) < 0.001


class TestIntersectionAgent:
    """Tests pour IntersectionAgent"""
    
    def test_intersection_creation(self):
        """Test la création d'une intersection"""
        model = MockModel()
        
        intersection = IntersectionAgent(
            unique_id="intersection_1",
            model=model,
            position=(500, 500)
        )
        
        assert intersection.unique_id == "intersection_1"
        assert intersection.position == (500, 500)
        assert len(intersection.traffic_lights) > 0
    
    def test_traffic_light_initialization(self):
        """Test l'initialisation des feux"""
        model = MockModel()
        
        intersection = IntersectionAgent(
            unique_id="intersection_1",
            model=model,
            position=(500, 500)
        )
        
        from agents.intersection_agent import TrafficLightState, Direction
        
        # Vérifier que les feux sont initialisés
        assert Direction.NORTH in intersection.traffic_lights
        
        # Vérifier l'alternance N-S / E-W
        ns_states = [intersection.traffic_lights[Direction.NORTH],
                    intersection.traffic_lights[Direction.SOUTH]]
        ew_states = [intersection.traffic_lights[Direction.EAST],
                    intersection.traffic_lights[Direction.WEST]]
        
        # N-S devrait être vert initialement
        assert TrafficLightState.GREEN in ns_states
        
        # E-W devrait être rouge initialement
        assert TrafficLightState.RED in ew_states
    
    def test_state_representation(self):
        """Test la représentation d'état pour Q-Learning"""
        model = MockModel()
        
        intersection = IntersectionAgent(
            unique_id="intersection_1",
            model=model,
            position=(500, 500)
        )
        
        # Ajouter des véhicules fictifs aux files
        from agents.intersection_agent import Direction
        intersection.queue_lengths[Direction.NORTH] = 5
        intersection.queue_lengths[Direction.SOUTH] = 3
        intersection.queue_lengths[Direction.EAST] = 2
        intersection.queue_lengths[Direction.WEST] = 1
        
        state = intersection._get_state_representation()
        
        # Devrait retourner une chaîne
        assert isinstance(state, str)
        assert len(state) > 0


class TestTrafficModel:
    """Tests pour le modèle principal"""
    
    def test_model_creation(self):
        """Test la création du modèle"""
        config_path = str(Path(__file__).parent.parent / "config.yaml")
        try:
            model = TrafficModel(config_path=config_path)
            
            assert model.width > 0
            assert model.height > 0
            assert len(model.intersections) > 0
            assert len(model.vehicles) > 0
            
        except FileNotFoundError:
            pytest.skip("Fichier config.yaml non trouvé")
    
    def test_model_step(self):
        """Test un pas de simulation"""
        config_path = str(Path(__file__).parent.parent / "config.yaml")
        try:
            model = TrafficModel(config_path=config_path)
            
            initial_step = model.current_step
            
            # Faire un pas
            model.step()
            
            # Vérifier que le compteur a augmenté
            assert model.current_step == initial_step + 1
            
        except FileNotFoundError:
            pytest.skip("Fichier config.yaml non trouvé")


class TestCommunication:
    """Tests pour le système de communication"""
    
    def test_fipa_message_creation(self):
        """Test la création d'un message FIPA"""
        from communication.fipa_message import FIPAMessage, Performative
        
        message = FIPAMessage(
            sender="agent_1",
            receiver="agent_2",
            performative=Performative.INFORM.value,
            content={"test": "data"}
        )
        
        assert message.sender == "agent_1"
        assert message.receiver == "agent_2"
        assert message.performative == "inform"
        assert message.content["test"] == "data"
    
    def test_message_reply(self):
        """Test la création d'une réponse"""
        from communication.fipa_message import FIPAMessage, Performative
        
        original = FIPAMessage(
            sender="agent_1",
            receiver="agent_2",
            performative=Performative.REQUEST.value,
            content={"action": "something"}
        )
        
        reply = original.create_reply(
            performative=Performative.AGREE.value,
            content={"status": "ok"}
        )
        
        # Vérifier l'inversion sender/receiver
        assert reply.sender == "agent_2"
        assert reply.receiver == "agent_1"
        assert reply.reply_to == original.message_id


class TestRouting:
    """Tests pour les algorithmes de routage"""
    
    def test_road_network_creation(self):
        """Test la création d'un réseau"""
        from algorithms.routing import RoadNetwork, Node
        
        network = RoadNetwork()
        
        # Ajouter des nœuds
        node1 = Node((0, 0), "node_1")
        node2 = Node((100, 0), "node_2")
        
        network.add_node(node1)
        network.add_node(node2)
        
        # Connecter
        network.add_edge("node_1", "node_2")
        
        assert len(network.nodes) == 2
        assert network.graph.number_of_edges() == 1
    
    def test_astar_routing(self):
        """Test le routage A*"""
        from algorithms.routing import RoadNetwork, AStarRouter
        
        # Créer un réseau simple
        network = RoadNetwork()
        network.create_grid_network(width=1000, height=1000, cell_size=100)
        
        router = AStarRouter(network)
        
        # Trouver un chemin
        path = router.find_path((0, 0), (500, 500))
        
        assert path is not None
        assert len(path) > 0
        # Le premier point devrait être proche de l'origine
        assert abs(path[0][0] - 0) < 100
        assert abs(path[0][1] - 0) < 100


class TestCrisisManagerAgent:
    """Tests pour l'Agent Gestionnaire de Crise"""
    
    def test_crisis_manager_creation(self):
        """Test la création du gestionnaire de crise"""
        from agents.crisis_manager_agent import CrisisManagerAgent
        
        model = MockModel()
        
        crisis_manager = CrisisManagerAgent(
            unique_id="crisis_manager",
            model=model
        )
        
        assert crisis_manager.unique_id == "crisis_manager"
        assert crisis_manager.interventions_count == 0
        assert crisis_manager.green_waves_created == 0
        assert crisis_manager.active_incidents == []
    
    def test_emergency_vehicle_registration(self):
        """Test l'enregistrement d'un véhicule d'urgence"""
        from agents.crisis_manager_agent import CrisisManagerAgent
        
        model = MockModel()
        crisis_manager = CrisisManagerAgent("crisis_manager", model)
        
        crisis_manager.register_emergency_vehicle(
            vehicle_id="ambulance_1",
            vehicle_type="ambulance",
            position=(100, 200),
            destination=(500, 500),
            route=[(100, 200), (300, 300), (500, 500)]
        )
        
        assert len(crisis_manager.emergency_vehicles) == 1
        assert crisis_manager.emergency_vehicles[0]['type'] == "ambulance"
    
    def test_crisis_manager_desire_generation(self):
        """Test la génération de désirs avec véhicules d'urgence"""
        from agents.crisis_manager_agent import CrisisManagerAgent
        from agents.bdi_agent import DesireType
        
        model = MockModel()
        crisis_manager = CrisisManagerAgent("crisis_manager", model)
        
        # Enregistrer un véhicule d'urgence
        crisis_manager.register_emergency_vehicle(
            vehicle_id="ambulance_1",
            vehicle_type="ambulance",
            position=(100, 200),
            destination=(500, 500)
        )
        
        # Générer les désirs
        crisis_manager.generate_desires()
        
        # Doit avoir le désir PRIORITIZE_EMERGENCY
        desire_types = [d.type for d in crisis_manager.desires]
        assert DesireType.PRIORITIZE_EMERGENCY in desire_types
    
    def test_crisis_manager_statistics(self):
        """Test les statistiques du gestionnaire de crise"""
        from agents.crisis_manager_agent import CrisisManagerAgent
        
        model = MockModel()
        crisis_manager = CrisisManagerAgent("crisis_manager", model)
        
        stats = crisis_manager.get_statistics()
        assert stats['id'] == "crisis_manager"
        assert stats['interventions_count'] == 0
        assert stats['green_waves_created'] == 0


class TestQLearning:
    """Tests pour l'implémentation Q-Learning"""
    
    def test_q_table_initialization(self):
        """Test l'initialisation de la Q-table"""
        model = MockModel()
        
        intersection = IntersectionAgent(
            unique_id="intersection_1",
            model=model,
            position=(500, 500)
        )
        
        # La Q-table doit être vide au départ
        assert intersection.q_table == {}
    
    def test_q_table_update(self):
        """Test la mise à jour de la Q-table (équation de Bellman)"""
        model = MockModel()
        
        intersection = IntersectionAgent(
            unique_id="intersection_1",
            model=model,
            position=(500, 500)
        )
        
        # Initialiser un état
        state = "2_1_NS"
        next_state = "1_2_EW"
        intersection.q_table[state] = {'change': 0.0, 'keep': 0.0}
        intersection.q_table[next_state] = {'change': 0.0, 'keep': 0.0}
        
        # Mettre à jour avec une récompense positive
        intersection._update_q_table(state, 'change', reward=5.0, next_state=next_state)
        
        # La valeur Q doit avoir augmenté
        assert intersection.q_table[state]['change'] > 0.0
        # keep doit rester à 0
        assert intersection.q_table[state]['keep'] == 0.0
    
    def test_reward_computation(self):
        """Test le calcul de la récompense"""
        model = MockModel()
        
        intersection = IntersectionAgent(
            unique_id="intersection_1",
            model=model,
            position=(500, 500)
        )
        
        from agents.intersection_agent import Direction
        
        # Simuler une situation avec des files d'attente
        intersection.queue_lengths[Direction.NORTH] = 5
        intersection.queue_lengths[Direction.SOUTH] = 3
        intersection.queue_lengths[Direction.EAST] = 2
        intersection.queue_lengths[Direction.WEST] = 1
        
        # Définir l'état précédent avec plus de véhicules en attente
        intersection.previous_total_waiting = 20.0
        
        reward = intersection._compute_reward()
        
        # La récompense doit être positive car les files ont diminué (20 -> 11)
        assert reward > 0


class TestContractNetProtocol:
    """Tests pour le Contract Net Protocol"""
    
    def test_cnp_message_creation(self):
        """Test la création d'un message CNP"""
        from communication.fipa_message import CommunicationProtocol
        
        cfp = CommunicationProtocol.contract_net_protocol(
            manager_id="crisis_manager",
            content={
                "task": "priority_delegation",
                "congested_intersection": "intersection_5"
            }
        )
        
        assert cfp.sender == "crisis_manager"
        assert cfp.receiver == "broadcast"
        assert cfp.protocol == "fipa-contract-net"
        assert cfp.content["type"] == "call_for_proposals"
    
    def test_cnp_proposal_creation(self):
        """Test la création d'une proposition CNP"""
        from communication.fipa_message import FIPAMessage, CommunicationProtocol
        
        # Créer un CFP d'abord
        cfp = CommunicationProtocol.contract_net_protocol(
            manager_id="crisis_manager",
            content={"task": "priority_delegation"}
        )
        
        # Créer une proposition en réponse
        proposal = CommunicationProtocol.propose_in_cnp(
            contractor_id="intersection_1",
            manager_id="crisis_manager",
            proposal_content={
                "task": "priority_delegation",
                "availability": 0.8
            },
            cfp_message=cfp
        )
        
        assert proposal.sender == "intersection_1"
        assert proposal.receiver == "crisis_manager"
        assert proposal.protocol == "fipa-contract-net"
        assert proposal.reply_to == cfp.message_id


class TestIntersectionEmergency:
    """Tests pour la gestion d'urgence dans les intersections"""
    
    def test_force_green(self):
        """Test le forçage du feu vert dans une direction"""
        model = MockModel()
        
        intersection = IntersectionAgent(
            unique_id="intersection_1",
            model=model,
            position=(500, 500)
        )
        
        from agents.intersection_agent import Direction, TrafficLightState
        
        # Forcer le vert vers l'Est
        intersection._force_green(Direction.EAST)
        
        # Est et Ouest doivent être verts
        assert intersection.traffic_lights[Direction.EAST] == TrafficLightState.GREEN
        assert intersection.traffic_lights[Direction.WEST] == TrafficLightState.GREEN
        
        # Nord et Sud doivent être rouges
        assert intersection.traffic_lights[Direction.NORTH] == TrafficLightState.RED
        assert intersection.traffic_lights[Direction.SOUTH] == TrafficLightState.RED


class TestVehicleType:
    """Tests pour les types de véhicules"""
    
    def test_standard_vehicle(self):
        """Test la création d'un véhicule standard"""
        model = MockModel()
        
        vehicle = VehicleAgent(
            unique_id="vehicle_1",
            model=model,
            position=(0, 0),
            destination=(100, 100)
        )
        
        assert vehicle.vehicle_type == "standard"
    
    def test_emergency_vehicle(self):
        """Test la création d'un véhicule d'urgence"""
        model = MockModel()
        
        ambulance = VehicleAgent(
            unique_id="ambulance_1",
            model=model,
            position=(0, 0),
            destination=(100, 100),
            vehicle_type="ambulance"
        )
        
        assert ambulance.vehicle_type == "ambulance"
    
    def test_bus_sotra(self):
        """Test la création d'un bus SOTRA"""
        model = MockModel()
        
        bus = VehicleAgent(
            unique_id="bus_1",
            model=model,
            position=(0, 0),
            destination=(100, 100),
            vehicle_type="bus_sotra"
        )
        
        assert bus.vehicle_type == "bus_sotra"


class TestScenarios:
    """Tests pour les scénarios"""
    
    def test_rush_hour_setup(self):
        """Test la configuration du scénario heure de pointe"""
        from scenarios.rush_hour import setup_scenario, get_origin_position, get_destination_position
        
        class MockModelWithConfig:
            config = {
                'scenarios': {
                    'rush_hour_morning': {
                        'name': 'Heure de pointe matinale',
                        'description': 'Flux Yopougon/Abobo vers Plateau',
                        'start_time': 0,
                        'duration': 3600,
                        'vehicle_generation_rate': 0.5,
                        'origin_zones': [
                            {'name': 'Yopougon', 'weight': 0.5, 'coordinates': [0, 2500]},
                            {'name': 'Abobo', 'weight': 0.5, 'coordinates': [2500, 5000]}
                        ],
                        'destination_zones': [
                            {'name': 'Plateau', 'weight': 1.0, 'coordinates': [2500, 0]}
                        ]
                    }
                }
            }
        
        model = MockModelWithConfig()
        scenario_info = setup_scenario(model)
        
        assert scenario_info['name'] == 'Heure de pointe matinale'
        assert scenario_info['vehicle_generation_rate'] == 0.5
        assert len(scenario_info['origin_zones']) == 2
        
        # Test des positions
        origin = get_origin_position(scenario_info)
        assert isinstance(origin, tuple)
        assert len(origin) == 2
        
        dest = get_destination_position(scenario_info)
        assert isinstance(dest, tuple)
        assert len(dest) == 2
    
    def test_incident_scenario_creation(self):
        """Test la création du scénario d'incident"""
        from scenarios.incident import IncidentScenario
        
        class MockModelWithConfig:
            config = {
                'scenarios': {
                    'incident_bridge': {
                        'name': 'Incident Pont De Gaulle',
                        'start_time': 1800,
                        'duration': 900,
                        'blocked_road': {
                            'name': 'Pont De Gaulle',
                            'coordinates': [[2500, 2000], [2500, 2500]]
                        },
                        'alternative_road': {
                            'name': 'Pont HKB',
                            'coordinates': [[3000, 2000], [3000, 2500]]
                        }
                    }
                }
            }
            time_step = 1.0
            road_network = None
            schedule = MockSchedule()
            vehicles = []
        
        model = MockModelWithConfig()
        scenario = IncidentScenario(model)
        
        assert scenario.name == 'Incident Pont De Gaulle'
        assert scenario.incident_start_time == 1800
        assert scenario.incident_duration == 900
        assert scenario.incident_active == False
        assert scenario.blocked_road_name == 'Pont De Gaulle'
        assert scenario.alternative_road_name == 'Pont HKB'


# Fonction pour exécuter tous les tests
def run_all_tests():
    """Exécute tous les tests"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_all_tests()
