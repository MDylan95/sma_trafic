# 🚦 Système Multi-Agent de Régulation du Trafic

Projet de simulation décentralisée pour réduire les embouteillages dans une zone urbaine dense (Abidjan) utilisant l'architecture BDI (Belief-Desire-Intention) et les systèmes multi-agents.

## 📋 Vue d'ensemble

Ce projet implémente un système intelligent et décentralisé pour gérer le trafic urbain où la décision est prise par l'interaction entre des entités autonomes (agents) plutôt que par un serveur central.

### Caractéristiques principales

- ✅ **Architecture BDI** pour tous les agents
- ✅ **Communication FIPA-ACL** standardisée
- ✅ **Algorithmes de routage** (A* et Dijkstra)
- ✅ **Optimisation des feux** (Q-Learning et Max-Pressure)
- ✅ **Scénarios réalistes** d'Abidjan
- ✅ **Coordination décentralisée** (ondes vertes)

## 🏗️ Architecture du Projet

```
traffic_sma_project/
│
├── agents/                          # Agents BDI
│   ├── bdi_agent.py                # Classe de base BDI
│   ├── vehicle_agent.py            # Agent Véhicule
│   ├── intersection_agent.py       # Agent Intersection
│   └── crisis_manager_agent.py     # Agent Gestionnaire de Crise
│
├── communication/                   # Système de communication
│   └── fipa_message.py             # Messages FIPA-ACL + Contract Net Protocol
│
├── algorithms/                      # Algorithmes
│   └── routing.py                  # A*, Dijkstra et routage dynamique
│
├── environment/                     # Environnement de simulation
│   └── traffic_model.py            # Modèle Mesa principal
│
├── scenarios/                       # Scénarios de test (Abidjan)
│   ├── rush_hour.py                # Heure de pointe Yopougon/Abobo → Plateau
│   └── incident.py                 # Incident Pont De Gaulle → Pont HKB
│
├── utils/                           # Utilitaires
│   └── database.py                 # Gestion PostgreSQL (7 tables)
│
├── visualizations/                  # Visualisation
│   └── charts.py                   # Graphiques, heatmaps et statistiques
│
├── data/                            # Données
│   ├── logs/                       # Logs de simulation
│   └── results/                    # Résultats et statistiques
│
├── sumo/                            # Intégration SUMO (visualisation temps réel)
│   ├── generate_network.py          # Génération du réseau SUMO (grille 6×6)
│   ├── sumo_connector.py            # Connecteur TraCI Mesa ↔ SUMO
│   ├── abidjan.sumocfg              # Configuration SUMO
│   ├── abidjan.net.xml              # Réseau routier compilé
│   ├── vtypes.add.xml               # Types de véhicules (standard, ambulance, bus...)
│   └── gui_settings.xml             # Paramètres d'affichage SUMO-GUI
│
├── tests/                           # Tests unitaires
│   └── test_agents.py              # Tests agents, communication, routage, scénarios
│
├── config.yaml                      # Configuration
├── requirements.txt                 # Dépendances Python
├── setup_database.py                # Script d'initialisation PostgreSQL
├── analyze_database.py              # Analyse interactive des simulations
├── main.py                          # Point d'entrée principal
└── README.md                        # Ce fichier
```

## 🎯 Les Trois Types d'Agents

### 1. Agent Véhicule (AV)
**Rôle**: Représente chaque véhicule circulant dans la simulation

**Perception**:
- Position actuelle
- Destination
- État du trafic environnant
- Messages des intersections

**Actions**:
- Accélérer / Décélérer
- Changer d'itinéraire
- S'arrêter aux feux rouges

**Objectifs**:
- Atteindre la destination
- Minimiser le temps de trajet
- Éviter les congestions

### 2. Agent Intersection (AI)
**Rôle**: Gère un carrefour avec feux de signalisation

**Perception**:
- Nombre de véhicules sur chaque voie
- État des intersections voisines
- Historique de trafic

**Actions**:
- Modifier la durée du feu vert/rouge
- Coordonner avec les intersections voisines
- Diffuser des informations de congestion

**Objectifs**:
- Maximiser le débit local
- Minimiser le temps d'attente moyen
- Créer des "ondes vertes" avec les voisins

### 3. Agent Gestionnaire de Crise
**Rôle**: Supervise les situations prioritaires (ambulances, bus SOTRA)

**Perception**:
- Véhicules d'urgence actifs et leurs positions
- État de congestion global
- Incidents en cours

**Actions**:
- Prioriser le passage des véhicules d'urgence (ambulances, bus SOTRA)
- Forcer des "vagues vertes" sur trajets spécifiques
- Déléguer la priorité aux intersections via le Contract Net Protocol
- Coordonner la réponse aux incidents

## 🚀 Installation

### Prérequis
- Python 3.8+
- pip

### Installation des dépendances

```bash
# Cloner le projet
git clone <votre-repo>
cd traffic_sma_project

# Installer les dépendances
pip install -r requirements.txt
```

## ▶️ Utilisation

### Lancement de la simulation

```bash
# Simulation basique
python main.py

# Avec graphiques statiques (KPIs, heatmap, réseau)
python main.py --visualize

# Avec SUMO-GUI (véhicules en mouvement en temps réel)
python main.py --sumo

# SUMO + graphiques + 500 pas
python main.py --sumo --visualize --steps 500

# Mode test rapide (100 pas)
python main.py --test --sumo

# Scénario spécifique
python main.py --scenario rush_hour

# Avec configuration personnalisée
python main.py --config custom_config.yaml
```

### Visualisation SUMO (véhicules en mouvement)

Le projet intègre **SUMO** (Simulation of Urban MObility) via **TraCI** pour visualiser les véhicules en temps réel :

```bash
# 1. Générer le réseau SUMO (une seule fois)
python sumo/generate_network.py

# 2. Lancer la simulation avec SUMO-GUI
python main.py --sumo --steps 500
```

SUMO-GUI affiche :
- 🚗 **Véhicules** en mouvement (bleu = standard, rouge = ambulance, vert = bus SOTRA)
- 🚦 **Feux de circulation** contrôlés par les agents Mesa (Q-Learning / Max-Pressure)
- 🗺️ **Réseau routier** en grille 6×6 (36 intersections, zone 2.5km × 2.5km)

Les décisions des agents Mesa (feux, routage) sont synchronisées en temps réel avec SUMO via TraCI.

### Configuration

Modifiez `config.yaml` pour ajuster:
- Durée de simulation
- Nombre de véhicules
- Paramètres des feux
- Algorithmes utilisés
- Scénarios activés

Exemple:
```yaml
simulation:
  duration: 3600  # 1 heure en secondes
  num_vehicles: 200

algorithms:
  routing:
    algorithm: "A_STAR"  # ou "DIJKSTRA"
  traffic_light:
    algorithm: "Q_LEARNING"  # ou "MAX_PRESSURE"
```

## 🗄️ Base de Données PostgreSQL

Le projet utilise **PostgreSQL** pour stocker et analyser l'historique des simulations.

### Configuration Rapide

```bash
# 1. Installer PostgreSQL
sudo apt install postgresql  # Ubuntu/Debian
brew install postgresql       # macOS

# 2. Configurer la base de données
python setup_database.py

# 3. C'est tout! Les simulations seront automatiquement sauvegardées
```

### Utilisation

```bash
# Lancer une simulation (sauvegarde automatique)
python main.py

# Analyser les résultats
python analyze_database.py
```

### Tables Créées

- `simulations` - Informations générales
- `vehicles` - Données des véhicules
- `intersections` - Performance des intersections
- `kpis_timeseries` - KPIs en temps réel
- `fipa_messages` - Historique des messages
- `vehicle_positions` - Positions (pour replay)

Voir le [Guide PostgreSQL](POSTGRESQL_GUIDE.md) pour plus de détails.

---

## 📊 Scénarios de Test

### 1. Heure de pointe matinale
**Description**: Flux massif Yopougon/Abobo → Plateau

**Configuration**:
```yaml
scenarios:
  rush_hour_morning:
    start_time: 0
    duration: 3600
    vehicle_generation_rate: 0.5  # véhicules/sec
```

**KPIs mesurés**:
- Temps de trajet moyen
- Longueur des files d'attente
- Niveau de congestion

### 2. Incident localisé
**Description**: Panne sur Pont De Gaulle → redirection vers Pont HKB

**Objectif**: Tester la capacité du système à s'adapter dynamiquement

## 📈 Indicateurs de Performance (KPIs)

| KPI | Description | Formule |
|-----|-------------|---------|
| **Temps de trajet moyen** | Temps moyen pour atteindre la destination | Σ(temps_trajet) / nb_véhicules |
| **Longueur moyenne des files** | Nombre moyen de véhicules en attente | Σ(longueur_file) / nb_intersections |
| **Messages échangés** | Volume de communication inter-agents | Total messages / temps |
| **Vitesse moyenne** | Vitesse moyenne du trafic | Σ(vitesse) / nb_véhicules |
| **Niveau de congestion** | Ratio de ralentissement | 1 - (vitesse_moy / vitesse_max) |

## 🧪 Tests

```bash
# Exécuter tous les tests
pytest

# Avec couverture
pytest --cov=. --cov-report=html

# Tests spécifiques
pytest tests/test_vehicle_agent.py
pytest tests/test_intersection_agent.py
```

## 📚 Algorithmes Implémentés

### Routage : A* (A-Star)
- **Avantage**: Optimal et rapide grâce à l'heuristique
- **Utilisation**: Calcul d'itinéraire initial et recalcul dynamique

### Optimisation des feux

#### 1. Q-Learning
- **Type**: Apprentissage par renforcement
- **Principe**: Les feux apprennent les meilleurs timings
- **Paramètres**:
  - Learning rate: 0.1
  - Discount factor: 0.9
  - Epsilon: 0.1 (exploration)

#### 2. Max-Pressure
- **Type**: Heuristique
- **Principe**: Prioriser les voies avec la plus forte "pression"
- **Formule**: Pression = Véhicules_entrants - Véhicules_sortants

### Coordination : Contract Net Protocol
- **Usage**: Négociation entre intersections
- **Étapes**:
  1. Appel d'offres (CFP)
  2. Propositions
  3. Acceptation/Rejet
  4. Exécution

## 📖 Communication FIPA-ACL

### Structure des messages

```python
FIPAMessage(
    sender="vehicle_1",
    receiver="intersection_5",
    performative="QUERY",
    content={
        "type": "route_request",
        "destination": (2500, 3000)
    },
    protocol="fipa-request"
)
```

### Performatives principaux

| Performative | Usage |
|--------------|-------|
| **INFORM** | Informer d'un fait |
| **REQUEST** | Demander une action |
| **PROPOSE** | Proposer une coordination |
| **ACCEPT** | Accepter une proposition |
| **REJECT** | Rejeter une proposition |
| **QUERY** | Demander de l'information |

## 📊 Visualisation

### Génération de graphiques

```python
from visualizations.charts import plot_kpis

# Charger les données
model = TrafficModel()
model.run_simulation(steps=1000)

# Générer les graphiques
plot_kpis(model.datacollector)
```

### Métriques disponibles
- Évolution du temps de trajet
- Niveau de congestion dans le temps
- Volume de messages échangés
- Carte de chaleur du trafic

## 🛠️ Développement

### Ajouter un nouveau type d'agent

```python
from agents.bdi_agent import BDIAgent, Desire, Intention

class MyAgent(BDIAgent):
    def perceive(self):
        # Implémenter la perception
        pass
    
    def generate_desires(self):
        # Générer les désirs
        pass
    
    def deliberate(self):
        # Créer les intentions
        pass
    
    def execute_intention(self, intention):
        # Exécuter une intention
        pass
```

### Ajouter un nouveau scénario

```python
# scenarios/my_scenario.py
def setup_scenario(model):
    # Configuration du scénario
    pass

def run_scenario(model):
    # Exécution
    pass
```

## 📝 Livrables

### 1. Code Source
- ✅ Dépôt GitHub/GitLab documenté
- ✅ README complet
- ✅ Code commenté
- ✅ Tests unitaires

### 2. Mémoire Technique
- Architecture du système
- Justification des choix
- Résultats des tests
- Analyse des performances

### 3. Démonstration
- Vidéo de la simulation
- Présentation des résultats
- Analyse comparative des algorithmes

## 🤝 Contribution

Les contributions sont bienvenues ! Veuillez:
1. Fork le projet
2. Créer une branche (`git checkout -b feature/AmazingFeature`)
3. Commit vos changements (`git commit -m 'Add AmazingFeature'`)
4. Push vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT.

## ✨ Auteurs

- Votre Nom - *Développement initial*

## 🙏 Remerciements

- Framework Mesa pour la simulation multi-agents
- FIPA pour les standards de communication
- Communauté Python pour les excellentes bibliothèques

## 📞 Contact

- Email: votre.email@example.com
- GitHub: [@votre-username](https://github.com/votre-username)

---

**Note**: Ce projet a été développé dans le cadre d'un projet académique sur les systèmes multi-agents appliqués à la régulation du trafic urbain.
