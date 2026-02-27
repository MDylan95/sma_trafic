# 🚀 Guide de Démarrage Rapide

## Installation en 5 minutes

### 1. Cloner le projet
```bash
git clone <votre-repo>
cd traffic_sma_project
```

### 2. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 3. Lancer votre première simulation
```bash
python main.py --test
```

C'est tout ! Vous venez de lancer votre première simulation multi-agents. 🎉

---

## Exemples d'Utilisation

### Simulation Standard (1 heure simulée)
```bash
python main.py
```

### Simulation Courte (Test)
```bash
python main.py --test
```

### Avec Scénario Heure de Pointe
```bash
python main.py --scenario rush_hour --steps 1000
```

### Mode Verbeux (pour debug)
```bash
python main.py --verbose
```

### Export des Résultats
```bash
python main.py --export results.json --export-csv data.csv
```

---

## Comprendre les Résultats

Après chaque simulation, vous obtenez :

### 📊 Statistiques Générales
```
  • Temps simulé: 3600 secondes (1 heure)
  • Véhicules créés: 200
  • Véhicules arrivés: 187
  • Véhicules actifs: 13
```

### 🎯 KPIs de Performance
```
  • Temps de trajet moyen: 245.67 secondes
  • Longueur moyenne des files: 3.45 véhicules
  • Vitesse moyenne: 8.23 m/s (29.63 km/h)
  • Niveau de congestion: 40.82%
```

### 💬 Communication
```
  • Messages totaux échangés: 1543
  • Types de messages:
    - inform: 892
    - propose: 453
    - accept: 198
```

---

## Personnaliser la Simulation

### Modifier le Nombre de Véhicules

Éditez `config.yaml`:
```yaml
simulation:
  num_vehicles: 500  # Au lieu de 200
```

### Changer l'Algorithme de Routage

```yaml
algorithms:
  routing:
    algorithm: "DIJKSTRA"  # Au lieu de A_STAR
```

### Activer le Q-Learning pour les Feux

```yaml
algorithms:
  traffic_light:
    algorithm: "Q_LEARNING"  # Au lieu de MAX_PRESSURE
    learning_rate: 0.1
    discount_factor: 0.9
```

---

## Générer des Visualisations

### Depuis Python

```python
from environment.traffic_model import TrafficModel
from visualizations.charts import plot_all_visualizations

# Créer et exécuter le modèle
model = TrafficModel()
model.run_simulation(steps=1000)

# Générer toutes les visualisations
plot_all_visualizations(model, output_dir="mes_resultats")
```

Les graphiques seront sauvegardés dans `mes_resultats/`:
- `network.png` - Le réseau routier
- `kpis.png` - Tous les KPIs
- `heatmap.png` - Carte de chaleur du trafic
- `summary.png` - Résumé statistique

---

## Créer un Nouveau Scénario

### 1. Créer le fichier de scénario

`scenarios/mon_scenario.py`:
```python
def setup_scenario(model):
    """Configure le scénario"""
    # Bloquer une route
    model.road_network.remove_edge("node_1", "node_2")
    
    # Ajouter des véhicules spécifiques
    for i in range(50):
        model._create_vehicle(f"scenario_vehicle_{i}")

def run_scenario(model):
    """Exécute le scénario"""
    model.run_simulation(steps=500)
```

### 2. Ajouter dans config.yaml

```yaml
scenarios:
  mon_scenario:
    name: "Mon Scénario Personnalisé"
    start_time: 0
    duration: 1800
```

---

## Tests Unitaires

### Lancer tous les tests
```bash
pytest
```

### Tester un composant spécifique
```bash
pytest tests/test_agents.py::TestVehicleAgent
```

### Avec couverture de code
```bash
pytest --cov=. --cov-report=html
```

Ouvrir `htmlcov/index.html` pour voir la couverture.

---

## Troubleshooting

### Problème : "ModuleNotFoundError"
**Solution** : Installer les dépendances
```bash
pip install -r requirements.txt
```

### Problème : "FileNotFoundError: config.yaml"
**Solution** : Exécuter depuis le répertoire racine
```bash
cd traffic_sma_project
python main.py
```

### Problème : Simulation très lente
**Solution** : Réduire le nombre de véhicules
```yaml
simulation:
  num_vehicles: 50  # Au lieu de 200
```

---

## Prochaines Étapes

### 📚 Apprendre Plus
- Lire le [README.md](README.md) complet
- Explorer les [exemples](examples/)
- Consulter la [documentation](docs/)

### 🔬 Expérimenter
- Comparer A* vs Dijkstra
- Tester Q-Learning vs Max-Pressure
- Créer vos propres scénarios

### 🎓 Approfondir
- Implémenter l'Agent Gestionnaire de Crise
- Ajouter des visualisations en temps réel
- Connecter à une vraie base de données

---

## Ressources

### Documentation
- [Architecture BDI](docs/bdi_architecture.md)
- [Protocole FIPA-ACL](docs/fipa_protocol.md)
- [Algorithmes de routage](docs/routing_algorithms.md)

### Exemples de Code
```python
# Exemple : Créer et configurer un véhicule
from agents.vehicle_agent import VehicleAgent

vehicle = VehicleAgent(
    unique_id="my_vehicle",
    model=model,
    position=(100, 100),
    destination=(1000, 1000),
    max_speed=15.0  # 54 km/h
)

# Exemple : Observer une intersection
intersection = model.intersections[0]
print(f"Files d'attente: {intersection.queue_lengths}")
print(f"État des feux: {intersection.traffic_lights}")
```

---

## Support

### Besoin d'aide ?
- 📧 Email: votre.email@example.com
- 💬 Discord: [Lien vers serveur]
- 🐛 Issues: [GitHub Issues](https://github.com/votre-repo/issues)

### Contribuer
Les contributions sont bienvenues ! Voir [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Bon code ! 🚀**
