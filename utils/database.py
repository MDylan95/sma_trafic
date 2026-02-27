"""
Module de gestion de la base de données PostgreSQL
Stockage et récupération des données de simulation
"""
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from typing import List, Dict, Optional, Any
import json
from datetime import datetime
from loguru import logger
import yaml


class PostgreSQLDatabase:
    """
    Gestionnaire de base de données PostgreSQL pour le système de trafic
    
    Gère:
    - Connexion à PostgreSQL
    - Création des tables
    - Insertion des logs de simulation
    - Récupération des statistiques
    - Analyse des performances
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialise la connexion à PostgreSQL
        
        Args:
            config_path: Chemin vers le fichier de configuration
        """
        # Charger la configuration
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        self.db_config = config['database']['postgresql']
        
        # Pool de connexions
        self.connection_pool = None
        self.initialize_pool()
        
        # Créer les tables si elles n'existent pas
        self.create_tables()
        
        logger.info("✅ Connexion PostgreSQL établie")
    
    def initialize_pool(self):
        """Initialise le pool de connexions"""
        try:
            conninfo = (
                f"host={self.db_config['host']} "
                f"port={self.db_config['port']} "
                f"dbname={self.db_config['database']} "
                f"user={self.db_config['user']} "
                f"password={self.db_config['password']}"
            )
            self.connection_pool = ConnectionPool(
                conninfo=conninfo,
                min_size=1,
                max_size=10
            )
            logger.info(f"Pool de connexions PostgreSQL créé: {self.db_config['database']}")
        except Exception as e:
            logger.error(f"Erreur lors de la création du pool: {e}")
            raise
    
    def get_connection(self):
        """Récupère une connexion du pool"""
        return self.connection_pool.getconn()
    
    def release_connection(self, conn):
        """Libère une connexion vers le pool"""
        self.connection_pool.putconn(conn)
    
    def create_tables(self):
        """Crée toutes les tables nécessaires"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Table des simulations
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulations (
                    simulation_id SERIAL PRIMARY KEY,
                    simulation_name VARCHAR(255),
                    scenario VARCHAR(100),
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    duration_seconds INTEGER,
                    num_vehicles INTEGER,
                    num_intersections INTEGER,
                    algorithm_routing VARCHAR(50),
                    algorithm_traffic_light VARCHAR(50),
                    config JSONB,
                    status VARCHAR(50) DEFAULT 'running'
                )
            """)
            
            # Table des véhicules
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicles (
                    vehicle_id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES simulations(simulation_id),
                    vehicle_unique_id VARCHAR(100),
                    origin_x FLOAT,
                    origin_y FLOAT,
                    destination_x FLOAT,
                    destination_y FLOAT,
                    creation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    arrival_time TIMESTAMP,
                    total_travel_time FLOAT,
                    distance_traveled FLOAT,
                    average_speed FLOAT,
                    route_changes INTEGER,
                    stops_count INTEGER,
                    reached_destination BOOLEAN
                )
            """)
            
            # Table des intersections
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intersections (
                    intersection_id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES simulations(simulation_id),
                    intersection_unique_id VARCHAR(100),
                    position_x FLOAT,
                    position_y FLOAT,
                    total_vehicles_processed INTEGER,
                    average_waiting_time FLOAT,
                    phase_changes INTEGER,
                    coordination_messages INTEGER
                )
            """)
            
            # Table des KPIs par pas de temps
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kpis_timeseries (
                    kpi_id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES simulations(simulation_id),
                    step INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    average_travel_time FLOAT,
                    average_queue_length FLOAT,
                    total_messages INTEGER,
                    active_vehicles INTEGER,
                    vehicles_arrived INTEGER,
                    average_speed FLOAT,
                    congestion_level FLOAT
                )
            """)
            
            # Table des messages FIPA
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fipa_messages (
                    message_id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES simulations(simulation_id),
                    sender VARCHAR(100),
                    receiver VARCHAR(100),
                    performative VARCHAR(50),
                    content JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    protocol VARCHAR(100)
                )
            """)
            
            # Table des événements de simulation
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS simulation_events (
                    event_id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES simulations(simulation_id),
                    event_type VARCHAR(100),
                    event_data JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Table des positions des véhicules (pour replay/animation)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vehicle_positions (
                    position_id SERIAL PRIMARY KEY,
                    simulation_id INTEGER REFERENCES simulations(simulation_id),
                    vehicle_unique_id VARCHAR(100),
                    step INTEGER,
                    position_x FLOAT,
                    position_y FLOAT,
                    speed FLOAT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Créer des index pour améliorer les performances
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vehicles_simulation 
                ON vehicles(simulation_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kpis_simulation 
                ON kpis_timeseries(simulation_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_simulation 
                ON fipa_messages(simulation_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_positions_simulation 
                ON vehicle_positions(simulation_id, step)
            """)
            
            conn.commit()
            logger.info("✅ Tables PostgreSQL créées/vérifiées")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur création tables: {e}")
            raise
        finally:
            cursor.close()
            self.release_connection(conn)
    
    # ============ GESTION DES SIMULATIONS ============
    
    def create_simulation(self, simulation_name: str, scenario: str, 
                         config: Dict) -> int:
        """
        Crée une nouvelle entrée de simulation
        
        Returns:
            simulation_id
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO simulations 
                (simulation_name, scenario, num_vehicles, num_intersections, 
                 algorithm_routing, algorithm_traffic_light, config)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING simulation_id
            """, (
                simulation_name,
                scenario,
                config.get('simulation', {}).get('num_vehicles', 0),
                0,  # Sera mis à jour plus tard
                config.get('algorithms', {}).get('routing', {}).get('algorithm', 'A_STAR'),
                config.get('algorithms', {}).get('traffic_light', {}).get('algorithm', 'Q_LEARNING'),
                json.dumps(config)
            ))
            
            simulation_id = cursor.fetchone()[0]
            conn.commit()
            
            logger.info(f"✅ Simulation créée avec ID: {simulation_id}")
            return simulation_id
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur création simulation: {e}")
            raise
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def update_simulation(self, simulation_id: int, **kwargs):
        """Met à jour une simulation"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            # Construire la requête dynamiquement
            update_fields = []
            values = []
            
            for key, value in kwargs.items():
                update_fields.append(f"{key} = %s")
                values.append(value)
            
            if update_fields:
                values.append(simulation_id)
                query = f"""
                    UPDATE simulations 
                    SET {', '.join(update_fields)}
                    WHERE simulation_id = %s
                """
                cursor.execute(query, values)
                conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur mise à jour simulation: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def end_simulation(self, simulation_id: int, duration_seconds: int):
        """Marque une simulation comme terminée"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE simulations
                SET end_time = CURRENT_TIMESTAMP,
                    duration_seconds = %s,
                    status = 'completed'
                WHERE simulation_id = %s
            """, (int(duration_seconds), simulation_id))
            conn.commit()
            logger.info(f"✅ Simulation {simulation_id} terminée")
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur fin simulation: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    # ============ INSERTION DES DONNÉES ============
    
    def insert_vehicle(self, simulation_id: int, vehicle_data: Dict):
        """Insère les données d'un véhicule"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO vehicles 
                (simulation_id, vehicle_unique_id, origin_x, origin_y, 
                 destination_x, destination_y, arrival_time, total_travel_time,
                 distance_traveled, average_speed, route_changes, 
                 stops_count, reached_destination)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                simulation_id,
                vehicle_data['id'],
                vehicle_data.get('origin_x'),
                vehicle_data.get('origin_y'),
                vehicle_data.get('destination_x'),
                vehicle_data.get('destination_y'),
                datetime.now() if vehicle_data.get('reached_destination') else None,
                vehicle_data.get('travel_time'),
                vehicle_data.get('distance_traveled'),
                vehicle_data.get('average_speed'),
                vehicle_data.get('route_changes'),
                vehicle_data.get('stops_count'),
                vehicle_data.get('reached_destination')
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur insertion véhicule: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def insert_vehicles_batch(self, simulation_id: int, vehicles_data: List[Dict]):
        """Insère plusieurs véhicules en batch (plus performant)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            values = [
                (
                    simulation_id,
                    v['id'],
                    v.get('origin_x'),
                    v.get('origin_y'),
                    v.get('destination_x'),
                    v.get('destination_y'),
                    datetime.now() if v.get('reached_destination') else None,
                    v.get('travel_time'),
                    v.get('distance_traveled'),
                    v.get('average_speed'),
                    v.get('route_changes'),
                    v.get('stops_count'),
                    v.get('reached_destination')
                )
                for v in vehicles_data
            ]
            
            cursor.executemany("""
                INSERT INTO vehicles 
                (simulation_id, vehicle_unique_id, origin_x, origin_y, 
                 destination_x, destination_y, arrival_time, total_travel_time,
                 distance_traveled, average_speed, route_changes, 
                 stops_count, reached_destination)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, values)
            
            conn.commit()
            logger.debug(f"✅ {len(vehicles_data)} véhicules insérés")
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur insertion batch véhicules: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def insert_intersection(self, simulation_id: int, intersection_data: Dict):
        """Insère les données d'une intersection"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO intersections 
                (simulation_id, intersection_unique_id, position_x, position_y,
                 total_vehicles_processed, average_waiting_time, 
                 phase_changes, coordination_messages)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                simulation_id,
                intersection_data['id'],
                intersection_data['position'][0],
                intersection_data['position'][1],
                intersection_data.get('total_vehicles_processed'),
                intersection_data.get('average_waiting_time'),
                intersection_data.get('phase_changes'),
                intersection_data.get('coordination_messages')
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur insertion intersection: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def insert_kpi_snapshot(self, simulation_id: int, step: int, kpis: Dict):
        """Insère un snapshot des KPIs pour un pas de temps"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO kpis_timeseries 
                (simulation_id, step, average_travel_time, average_queue_length,
                 total_messages, active_vehicles, vehicles_arrived, 
                 average_speed, congestion_level)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                simulation_id,
                step,
                kpis.get('Average_Travel_Time'),
                kpis.get('Average_Queue_Length'),
                kpis.get('Total_Messages'),
                kpis.get('Active_Vehicles'),
                kpis.get('Vehicles_Arrived'),
                kpis.get('Average_Speed'),
                kpis.get('Congestion_Level')
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur insertion KPIs: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def insert_message(self, simulation_id: int, message):
        """Insère un message FIPA"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO fipa_messages 
                (simulation_id, sender, receiver, performative, content, protocol)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                simulation_id,
                message.sender,
                message.receiver,
                message.performative,
                json.dumps(message.content),
                message.protocol
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur insertion message: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def insert_vehicle_position(self, simulation_id: int, vehicle_id: str, 
                               step: int, position: tuple, speed: float):
        """Insère la position d'un véhicule (pour animation)"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO vehicle_positions 
                (simulation_id, vehicle_unique_id, step, position_x, position_y, speed)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                simulation_id,
                vehicle_id,
                step,
                position[0],
                position[1],
                speed
            ))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            logger.error(f"❌ Erreur insertion position: {e}")
        finally:
            cursor.close()
            self.release_connection(conn)
    
    # ============ RÉCUPÉRATION DES DONNÉES ============
    
    def get_simulation(self, simulation_id: int) -> Optional[Dict]:
        """Récupère les informations d'une simulation"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(row_factory=dict_row)
            
            cursor.execute("""
                SELECT * FROM simulations WHERE simulation_id = %s
            """, (simulation_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
            
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def get_all_simulations(self) -> List[Dict]:
        """Récupère toutes les simulations"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(row_factory=dict_row)
            
            cursor.execute("""
                SELECT * FROM simulations ORDER BY start_time DESC
            """)
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def get_kpis_timeseries(self, simulation_id: int) -> List[Dict]:
        """Récupère la série temporelle des KPIs"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(row_factory=dict_row)
            
            cursor.execute("""
                SELECT * FROM kpis_timeseries 
                WHERE simulation_id = %s 
                ORDER BY step
            """, (simulation_id,))
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def get_simulation_statistics(self, simulation_id: int) -> Dict:
        """Calcule les statistiques agrégées d'une simulation"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(row_factory=dict_row)
            
            # Statistiques des véhicules
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_vehicles,
                    COUNT(*) FILTER (WHERE reached_destination) as vehicles_arrived,
                    AVG(total_travel_time) as avg_travel_time,
                    AVG(distance_traveled) as avg_distance,
                    AVG(average_speed) as avg_speed,
                    AVG(route_changes) as avg_route_changes
                FROM vehicles
                WHERE simulation_id = %s
            """, (simulation_id,))
            
            vehicle_stats = dict(cursor.fetchone())
            
            # Statistiques des intersections
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_intersections,
                    AVG(average_waiting_time) as avg_waiting_time,
                    SUM(phase_changes) as total_phase_changes,
                    SUM(coordination_messages) as total_coordination_msgs
                FROM intersections
                WHERE simulation_id = %s
            """, (simulation_id,))
            
            intersection_stats = dict(cursor.fetchone())
            
            # Statistiques des messages
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_messages,
                    COUNT(DISTINCT performative) as unique_performatives
                FROM fipa_messages
                WHERE simulation_id = %s
            """, (simulation_id,))
            
            message_stats = dict(cursor.fetchone())
            
            return {
                'vehicles': vehicle_stats,
                'intersections': intersection_stats,
                'messages': message_stats
            }
            
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def compare_simulations(self, simulation_ids: List[int]) -> Dict:
        """Compare plusieurs simulations"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(row_factory=dict_row)
            
            placeholders = ','.join(['%s'] * len(simulation_ids))
            
            cursor.execute(f"""
                SELECT 
                    s.simulation_id,
                    s.simulation_name,
                    s.scenario,
                    s.algorithm_routing,
                    s.algorithm_traffic_light,
                    AVG(v.total_travel_time) as avg_travel_time,
                    AVG(k.congestion_level) as avg_congestion
                FROM simulations s
                LEFT JOIN vehicles v ON s.simulation_id = v.simulation_id
                LEFT JOIN kpis_timeseries k ON s.simulation_id = k.simulation_id
                WHERE s.simulation_id IN ({placeholders})
                GROUP BY s.simulation_id
            """, simulation_ids)
            
            return [dict(row) for row in cursor.fetchall()]
            
        finally:
            cursor.close()
            self.release_connection(conn)
    
    def get_vehicles(self, simulation_id: int) -> List[Dict]:
        """Récupère tous les véhicules d'une simulation"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(row_factory=dict_row)
            cursor.execute("""
                SELECT * FROM vehicles
                WHERE simulation_id = %s
                ORDER BY vehicle_id
            """, (simulation_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            self.release_connection(conn)

    def get_intersections(self, simulation_id: int) -> List[Dict]:
        """Récupère toutes les intersections d'une simulation"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor(row_factory=dict_row)
            cursor.execute("""
                SELECT * FROM intersections
                WHERE simulation_id = %s
                ORDER BY intersection_id
            """, (simulation_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            cursor.close()
            self.release_connection(conn)

    # ============ NETTOYAGE ============
    
    def close(self):
        """Ferme toutes les connexions"""
        if self.connection_pool:
            self.connection_pool.close()
            logger.info("✅ Connexions PostgreSQL fermées")
    
    def __del__(self):
        """Destructeur"""
        self.close()


# Fonction helper pour créer la base de données
def setup_database(db_name: str = "traffic_sma", 
                   user: str = "postgres", 
                   password: str = "1030",
                   host: str = "localhost",
                   port: int = 5432):
    """
    Crée la base de données si elle n'existe pas
    
    Usage:
        setup_database("traffic_sma", "postgres", "mypassword")
    """
    # Connexion à la base postgres par défaut
    conn = psycopg.connect(
        dbname="postgres",
        user=user,
        password=password,
        host=host,
        port=port,
        autocommit=True
    )
    cursor = conn.cursor()
    
    # Vérifier si la base existe
    cursor.execute("""
        SELECT 1 FROM pg_database WHERE datname = %s
    """, (db_name,))
    
    if not cursor.fetchone():
        # Créer la base
        cursor.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(
            psycopg.sql.Identifier(db_name)
        ))
        print(f"✅ Base de données '{db_name}' créée")
    else:
        print(f"ℹ️  Base de données '{db_name}' existe déjà")
    
    cursor.close()
    conn.close()


if __name__ == "__main__":
    # Test de connexion
    print("Test de connexion PostgreSQL...")
    
    # Créer la base si nécessaire
    setup_database()
    
    # Tester la connexion
    db = PostgreSQLDatabase()
    print("✅ Connexion réussie!")
    
    # Afficher les tables
    print("\nTables créées:")
    print("  - simulations")
    print("  - vehicles")
    print("  - intersections")
    print("  - kpis_timeseries")
    print("  - fipa_messages")
    print("  - simulation_events")
    print("  - vehicle_positions")
    
    db.close()
