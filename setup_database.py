"""
Script de configuration de la base de données PostgreSQL
Pour initialiser la base de données avant la première utilisation
"""
import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import PostgreSQLDatabase, setup_database
from loguru import logger
import yaml


def load_config():
    """Charge la configuration"""
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.error("❌ Fichier config.yaml non trouvé")
        sys.exit(1)


def main():
    """Configure la base de données PostgreSQL"""
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║     🗄️  CONFIGURATION BASE DE DONNÉES POSTGRESQL 🗄️          ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    # Charger la configuration
    config = load_config()
    db_config = config['database']['postgresql']
    
    print("\n📋 Configuration détectée:")
    print(f"  • Host: {db_config['host']}")
    print(f"  • Port: {db_config['port']}")
    print(f"  • Database: {db_config['database']}")
    print(f"  • User: {db_config['user']}")
    
    print("\n🔧 Étapes de configuration:\n")
    
    # Étape 1: Créer la base de données
    print("1️⃣  Création de la base de données...")
    try:
        setup_database(
            db_name=db_config['database'],
            user=db_config['user'],
            password=db_config['password'],
            host=db_config['host'],
            port=db_config['port']
        )
        print("   ✅ Base de données prête\n")
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        print("\n⚠️  Vérifiez que:")
        print("   1. PostgreSQL est installé et démarré")
        print("   2. Les identifiants dans config.yaml sont corrects")
        print("   3. L'utilisateur a les droits de création de base")
        sys.exit(1)
    
    # Étape 2: Créer les tables
    print("2️⃣  Création des tables...")
    try:
        db = PostgreSQLDatabase()
        print("   ✅ Tables créées avec succès\n")
        
        # Afficher les tables créées
        print("   📊 Tables disponibles:")
        tables = [
            "simulations",
            "vehicles", 
            "intersections",
            "kpis_timeseries",
            "fipa_messages",
            "simulation_events",
            "vehicle_positions"
        ]
        for table in tables:
            print(f"      • {table}")
        
        db.close()
        
    except Exception as e:
        print(f"   ❌ Erreur création tables: {e}")
        sys.exit(1)
    
    # Étape 3: Test de connexion
    sim_id = None
    print("\n3️⃣  Test de connexion...")
    try:
        db = PostgreSQLDatabase()
        
        # Test d'insertion simple
        sim_id = db.create_simulation(
            simulation_name="Test Configuration",
            scenario="test",
            config=config
        )
        
        print(f"   ✅ Test réussi (simulation_id: {sim_id})")
        
        # Nettoyer le test
        db.close()
        
    except Exception as e:
        print(f"   ❌ Erreur test: {e}")
        sys.exit(1)
    
    # Résumé
    print("\n" + "="*70)
    print("✅ CONFIGURATION TERMINÉE AVEC SUCCÈS!")
    print("="*70)
    
    print("\n📝 Prochaines étapes:")
    print("  1. Lancez une simulation: python main.py --test")
    print("  2. Les données seront automatiquement sauvegardées dans PostgreSQL")
    print("  3. Consultez les résultats avec des requêtes SQL")
    
    example_id = sim_id if sim_id is not None else 1
    print("\n💡 Exemples de requêtes SQL:")
    print(f"""
    -- Lister toutes les simulations
    SELECT * FROM simulations ORDER BY start_time DESC;
    
    -- Statistiques d'une simulation
    SELECT 
        AVG(total_travel_time) as avg_time,
        AVG(average_speed) as avg_speed
    FROM vehicles 
    WHERE simulation_id = {example_id};
    
    -- Évolution des KPIs
    SELECT step, average_speed, congestion_level 
    FROM kpis_timeseries 
    WHERE simulation_id = {example_id} 
    ORDER BY step;
    """)
    
    print("\n🎉 Base de données prête à l'emploi!\n")


if __name__ == "__main__":
    main()
