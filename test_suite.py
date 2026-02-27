"""
Suite de tests automatisés pour valider les composants du projet
avant de lancer la simulation complète.

Usage:
    python test_suite.py
"""
import os
import sys
import yaml
from pathlib import Path

# Couleurs pour l'affichage
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(name, passed, details=""):
    """Affiche le résultat d'un test"""
    status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
    print(f"  {status} {name}")
    if details and not passed:
        print(f"      → {Colors.YELLOW}{details}{Colors.RESET}")

def test_file_structure():
    """Vérifie que tous les fichiers essentiels existent"""
    print(f"\n{Colors.BLUE}[1] Structure des fichiers{Colors.RESET}")
    
    required_files = [
        "config.yaml",
        "main.py",
        "setup_database.py",
        "requirements.txt",
        "agents/bdi_agent.py",
        "agents/vehicle_agent.py",
        "agents/intersection_agent.py",
        "agents/crisis_manager_agent.py",
        "communication/fipa_message.py",
        "algorithms/routing.py",
        "environment/traffic_model.py",
        "scenarios/rush_hour.py",
        "scenarios/incident.py",
        "sumo_integration/generate_network.py",
        "sumo_integration/sumo_connector.py",
        "visualizations/charts.py",
        "utils/database.py",
    ]
    
    all_exist = True
    for file in required_files:
        exists = os.path.exists(file)
        print_test(file, exists, "Fichier manquant" if not exists else "")
        all_exist = all_exist and exists
    
    return all_exist

def test_config_yaml():
    """Vérifie la cohérence du fichier config.yaml"""
    print(f"\n{Colors.BLUE}[2] Configuration (config.yaml){Colors.RESET}")
    
    try:
        with open("config.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Vérifier les sections principales
        sections = ['simulation', 'environment', 'intersection', 'vehicle', 
                   'communication', 'algorithms', 'scenarios', 'database']
        all_ok = True
        
        for section in sections:
            exists = section in config
            print_test(f"Section '{section}'", exists, f"Section manquante")
            all_ok = all_ok and exists
        
        # Vérifier les coordonnées du Pont De Gaulle
        if 'scenarios' in config and 'incident_bridge' in config['scenarios']:
            incident = config['scenarios']['incident_bridge']
            coords = incident.get('blocked_road', {}).get('coordinates', [])
            
            # Les coordonnées doivent être [[2000, y1], [2000, y2]] pour le Pont De Gaulle (col=2)
            if coords and len(coords) == 2:
                x1, x2 = coords[0][0], coords[1][0]
                correct = (x1 == 2000 and x2 == 2000)
                print_test(
                    "Coordonnées Pont De Gaulle (x=2000)", 
                    correct,
                    f"Coordonnées incorrectes: {coords}. Attendu: x=2000"
                )
                all_ok = all_ok and correct
            else:
                print_test("Coordonnées Pont De Gaulle", False, "Format invalide")
                all_ok = False
        
        # Vérifier la base de données
        if 'database' in config and 'postgresql' in config['database']:
            db = config['database']['postgresql']
            required_db_fields = ['host', 'port', 'database', 'user', 'password']
            for field in required_db_fields:
                exists = field in db
                print_test(f"DB config '{field}'", exists, f"Champ manquant")
                all_ok = all_ok and exists
        
        return all_ok
        
    except Exception as e:
        print_test("Lecture config.yaml", False, str(e))
        return False

def test_imports():
    """Vérifie que les imports Python fonctionnent"""
    print(f"\n{Colors.BLUE}[3] Imports Python{Colors.RESET}")
    
    modules = [
        ("mesa", "Framework Mesa"),
        ("numpy", "NumPy"),
        ("pandas", "Pandas"),
        ("matplotlib", "Matplotlib"),
        ("yaml", "PyYAML"),
        ("psycopg2", "PostgreSQL driver"),
        ("loguru", "Loguru"),
    ]
    
    all_ok = True
    for module_name, description in modules:
        try:
            __import__(module_name)
            print_test(description, True)
        except ImportError:
            print_test(description, False, f"Installer avec: pip install {module_name}")
            all_ok = False
    
    # SUMO (optionnel mais recommandé)
    try:
        import traci
        import sumolib
        print_test("SUMO (traci/sumolib)", True)
    except ImportError:
        print_test("SUMO (traci/sumolib)", False, 
                  "Optionnel. Installer avec: pip install eclipse-sumo traci sumolib")
    
    return all_ok

def test_sumo_network():
    """Vérifie que les fichiers SUMO sont générés"""
    print(f"\n{Colors.BLUE}[4] Réseau SUMO{Colors.RESET}")
    
    sumo_files = [
        "sumo_integration/abidjan.net.xml",
        "sumo_integration/abidjan.sumocfg",
        "sumo_integration/routes.rou.xml",
        "sumo_integration/vtypes.add.xml",
    ]
    
    all_exist = True
    for file in sumo_files:
        exists = os.path.exists(file)
        print_test(file, exists, 
                  "Générer avec: python sumo_integration/generate_network.py" if not exists else "")
        all_exist = all_exist and exists
    
    return all_exist

def test_database_connection():
    """Teste la connexion à PostgreSQL"""
    print(f"\n{Colors.BLUE}[5] Base de données PostgreSQL{Colors.RESET}")
    
    try:
        import psycopg2
        with open("config.yaml", 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        db_config = config['database']['postgresql']
        
        # Tentative de connexion
        try:
            conn = psycopg2.connect(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password']
            )
            print_test("Connexion PostgreSQL", True)
            
            # Vérifier que les tables existent
            cursor = conn.cursor()
            tables = ['simulations', 'vehicles', 'intersections', 'kpis_timeseries', 'fipa_messages']
            all_tables_exist = True
            
            for table in tables:
                cursor.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)",
                    (table,)
                )
                exists = cursor.fetchone()[0]
                print_test(f"Table '{table}'", exists, 
                          "Créer avec: python setup_database.py" if not exists else "")
                all_tables_exist = all_tables_exist and exists
            
            cursor.close()
            conn.close()
            return all_tables_exist
            
        except psycopg2.OperationalError as e:
            print_test("Connexion PostgreSQL", False, str(e))
            return False
            
    except Exception as e:
        print_test("Test base de données", False, str(e))
        return False

def test_code_consistency():
    """Vérifie la cohérence du code (imports, syntaxe basique)"""
    print(f"\n{Colors.BLUE}[6] Cohérence du code{Colors.RESET}")
    
    # Tester l'import des modules principaux
    modules_to_test = [
        ("agents.bdi_agent", "BDIAgent"),
        ("agents.vehicle_agent", "VehicleAgent"),
        ("agents.intersection_agent", "IntersectionAgent"),
        ("agents.crisis_manager_agent", "CrisisManagerAgent"),
        ("communication.fipa_message", "FIPAMessage"),
        ("algorithms.routing", "RoadNetwork"),
        ("environment.traffic_model", "TrafficModel"),
    ]
    
    all_ok = True
    for module_path, class_name in modules_to_test:
        try:
            module = __import__(module_path, fromlist=[class_name])
            getattr(module, class_name)
            print_test(f"{module_path}.{class_name}", True)
        except Exception as e:
            print_test(f"{module_path}.{class_name}", False, str(e))
            all_ok = False
    
    return all_ok

def main():
    """Exécute tous les tests"""
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}🧪 SUITE DE TESTS - Système Multi-Agent de Trafic{Colors.RESET}")
    print(f"{'='*60}")
    
    results = {
        "Structure des fichiers": test_file_structure(),
        "Configuration YAML": test_config_yaml(),
        "Imports Python": test_imports(),
        "Réseau SUMO": test_sumo_network(),
        "Base de données": test_database_connection(),
        "Cohérence du code": test_code_consistency(),
    }
    
    # Résumé
    print(f"\n{'='*60}")
    print(f"{Colors.BLUE}📊 RÉSUMÉ{Colors.RESET}")
    print(f"{'='*60}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}✓{Colors.RESET}" if result else f"{Colors.RED}✗{Colors.RESET}"
        print(f"  {status} {test_name}")
    
    print(f"\n{Colors.BLUE}Score: {passed}/{total}{Colors.RESET}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}✅ Tous les tests sont passés ! Le projet est prêt pour la simulation.{Colors.RESET}")
        print(f"\nLancer la simulation avec:")
        print(f"  {Colors.YELLOW}python main.py --sumo --sumo-interactive --steps 1000{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}❌ {total - passed} test(s) échoué(s). Corrigez les erreurs avant de lancer la simulation.{Colors.RESET}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
