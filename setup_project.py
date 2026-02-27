"""
Script d'initialisation de la structure du projet SMA Traffic
"""
import os

def create_project_structure():
    """Crée la structure complète du projet"""
    
    directories = [
        "agents",
        "agents/behaviors",
        "environment",
        "communication",
        "algorithms",
        "scenarios",
        "utils",
        "tests",
        "data",
        "data/logs",
        "data/results",
        "visualizations",
        "docs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        # Créer un __init__.py pour chaque package Python
        if directory not in ["data", "data/logs", "data/results", "docs"]:
            init_file = os.path.join(directory, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write(f'"""\n{directory.replace("/", ".")} package\n"""\n')
    
    print("✅ Structure du projet créée avec succès!")
    print("\nArborescence:")
    for directory in directories:
        print(f"  📁 {directory}")

if __name__ == "__main__":
    create_project_structure()
