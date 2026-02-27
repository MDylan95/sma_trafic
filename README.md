# 🚦 Système Multi-Agent de Régulation du Trafic Urbain - Abidjan

Simulation multi-agent avancée du trafic urbain d'Abidjan (Côte d'Ivoire) utilisant l'architecture BDI (Belief-Desire-Intention), le réseau routier réel OpenStreetMap, et l'intégration SUMO pour une visualisation microscopique en temps réel.

## 📋 Vue d'ensemble

Ce projet implémente un système intelligent et décentralisé pour gérer le trafic urbain d'Abidjan, où les décisions sont prises par l'interaction entre des agents autonomes (véhicules, intersections, gestionnaire de crise) plutôt que par un contrôle centralisé.

### Caractéristiques principales

- ✅ **Réseau routier réel** : Données OpenStreetMap d'Abidjan (~5000 edges)
- ✅ **Intégration SUMO** : Visualisation microscopique via TraCI
- ✅ **Architecture BDI** : Agents autonomes avec croyances, désirs, intentions
- ✅ **Communication FIPA-ACL** : Messages standardisés inter-agents
- ✅ **Scénarios réalistes** : Heures de pointe (Yopougon/Abobo → Plateau), incidents (Pont De Gaulle)
- ✅ **Base de données PostgreSQL** : Stockage et analyse des KPIs
- ✅ **Optimisations performance** : 300+ véhicules simultanés, 0.3s/step

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
├── sumo_integration/                # Intégration SUMO (visualisation temps réel)
│   ├── sumo_connector.py            # Connecteur TraCI Mesa ↔ SUMO
│   ├── abidjan_real.net.xml         # Réseau routier OSM Abidjan (~5000 edges)
│   ├── abidjan_real.osm.xml         # Données OpenStreetMap brutes
│   ├── abidjan_real.sumocfg         # Configuration SUMO
│   ├── real_network_constants.py    # Constantes géographiques (Pont De Gaulle, HKB, zones)
│   ├── vtypes.add.xml               # Types de véhicules (standard, ambulance, bus SOTRA)
│   ├── gui_settings.xml             # Paramètres d'affichage SUMO-GUI
│   └── import_real_abidjan.py       # Script d'import OSM → SUMO
│
├── tests/                           # Tests unitaires
│   └── test_agents.py              # Tests agents, communication, routage, scénarios
│
├── config.yaml                      # Configuration
├── requirements.txt                 # Dépendances Python
├── setup_database.py                # Script d'initialisation PostgreSQL
├── analyze_database.py              # Analyse interactive des simulations
├── main.py                          # Point d'entrée principal
│
├── MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md  # Mémoire technique complet (67 pages)
├── RAPPORT_CONFORMITE_CAHIER_DES_CHARGES.md  # Rapport de conformité
├── DOCUMENTATION_SCENARIOS_TEST.md  # Documentation des scénarios
├── OPTIMISATIONS_PERFORMANCE.md     # Optimisations appliquées
├── POSTGRESQL_GUIDE.md              # Guide PostgreSQL
├── TESTING_GUIDE.md                 # Guide de test
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
- Python 3.10+
- SUMO 1.15.0+ (avec SUMO-GUI)
- PostgreSQL 14+ (optionnel, pour sauvegarde des KPIs)
- pip

### Installation

```bash
# 1. Cloner le projet
git clone https://github.com/MDylan95/sma_trafic.git
cd sma_trafic

# 2. Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 3. Installer les dépendances Python
pip install -r requirements.txt

# 4. Installer SUMO (si pas déjà installé)
# Ubuntu/Debian
sudo apt-get install sumo sumo-tools sumo-gui

# macOS
brew install sumo

# Windows: Télécharger depuis https://sumo.dlr.de/docs/Downloads.php

# 5. Configurer PostgreSQL (optionnel)
python setup_database.py
```

## ▶️ Utilisation

### Lancement de la simulation

```bash
# Simulation basique (sans visualisation)
python main.py --steps 500

# Avec SUMO-GUI (visualisation temps réel sur réseau OSM Abidjan)
python main.py --sumo --sumo-interactive --steps 1000

# Scénario heure de pointe (Yopougon/Abobo → Plateau)
python main.py --sumo --sumo-interactive --scenario rush_hour --steps 1000

# Scénario incident (Pont De Gaulle bloqué → redirection Pont HKB)
python main.py --sumo --sumo-interactive --scenario incident --steps 1800

# Mode test rapide (100 pas)
python main.py --test --steps 100

# Avec sauvegarde PostgreSQL
python main.py --sumo --database --steps 1000

# Avec configuration personnalisée
python main.py --config custom_config.yaml
```

### Visualisation SUMO (réseau réel OSM Abidjan)

Le projet intègre **SUMO** (Simulation of Urban MObility) via **TraCI** pour visualiser les véhicules sur le réseau routier réel d'Abidjan :

```bash
# Lancer la simulation avec SUMO-GUI
python main.py --sumo --sumo-interactive --scenario rush_hour --steps 1000
```

**SUMO-GUI affiche :**
- 🗺️ **Réseau routier réel** : OpenStreetMap d'Abidjan (~5000 edges)
- 🌉 **Infrastructures critiques** : Pont De Gaulle, Pont HKB
- 🏘️ **Zones géographiques** : Yopougon, Abobo, Plateau, Cocody, Treichville
- 🚗 **Véhicules** en mouvement (bleu = standard, rouge = ambulance, vert = bus SOTRA)
- 🚦 **Feux de circulation** contrôlés par les agents Mesa
- 🚨 **Incidents** visualisés (polygone rouge sur pont bloqué)

**Synchronisation Mesa ↔ SUMO :**
- Les agents Mesa créent des véhicules avec coordonnées GPS (lon, lat)
- SUMO Connector convertit GPS → edges SUMO via `find_edge_near_coords()`
- Les décisions des agents (feux, routage) sont appliquées en temps réel dans SUMO via TraCI

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

### 1. Scénario Rush Hour (Heure de Pointe)
**Description**: Simulation du flux massif matinal Yopougon/Abobo → Plateau

**Configuration** (`config.yaml`):
```yaml
scenarios:
  rush_hour_morning:
    name: "Heure de pointe matinale"
    origin_zones:
      - name: "Yopougon"
        weight: 0.5
        bbox: [-4.070, 5.320, -4.010, 5.380]  # Coordonnées GPS
      - name: "Abobo"
        weight: 0.5
        bbox: [-4.030, 5.410, -3.970, 5.470]
    destination_zones:
      - name: "Plateau"
        weight: 1.0
        bbox: [-4.020, 5.300, -3.970, 5.360]
    vehicle_generation_rate: 2.0  # véhicules/seconde
    use_real_coords: true  # Utiliser coordonnées GPS réelles
```

**Lancement**:
```bash
python main.py --sumo --sumo-interactive --scenario rush_hour --steps 1000
```

**KPIs mesurés**:
- Temps de trajet moyen (Yopougon/Abobo → Plateau)
- Longueur des files d'attente aux carrefours
- Congestion sur Pont De Gaulle et Pont HKB
- Nombre de messages FIPA-ACL échangés

---

### 2. Scénario Incident (Pont De Gaulle Bloqué)
**Description**: Panne de véhicule bloquant le Pont De Gaulle → redirection automatique vers Pont HKB

**Configuration** (`config.yaml`):
```yaml
scenarios:
  incident_bridge:
    name: "Incident Pont De Gaulle"
    start_time: 300      # Déclenchement après 5 minutes
    duration: 120        # Durée de l'incident : 2 minutes
    blocked_road:
      name: "Pont De Gaulle"
      edges: ["edge_id_1", "edge_id_2"]  # Edges SUMO réels
    alternative_road:
      name: "Pont HKB"
      edges: ["edge_id_3", "edge_id_4"]
```

**Lancement**:
```bash
python main.py --sumo --sumo-interactive --scenario incident --steps 1800
```

**Déroulement**:
1. **Phase 1 (0-300s)** : Trafic normal
2. **Phase 2 (300s)** : Déclenchement incident → Pont De Gaulle bloqué (polygone rouge dans SUMO)
3. **Phase 3 (300-420s)** : Véhicules re-routés vers Pont HKB, diffusion messages FIPA-ACL
4. **Phase 4 (420s)** : Résolution incident → Pont De Gaulle restauré
5. **Phase 5 (420s+)** : Retour à la normale

**KPIs mesurés**:
- Temps de réaction du système (détection → redirection)
- Augmentation du trafic sur Pont HKB pendant l'incident
- Temps de trajet moyen avant/pendant/après incident
- Nombre de véhicules re-routés

**Objectif**: Valider la capacité du système à s'adapter dynamiquement aux incidents

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

- **Mac-Dylan KACOU** ([@MDylan95](https://github.com/MDylan95)) - *Développement initial*

## 🙏 Remerciements

- Framework Mesa pour la simulation multi-agents
- FIPA pour les standards de communication
- Communauté Python pour les excellentes bibliothèques

## 📞 Contact

- Email: macdylankacou2000@gmail.com
- GitHub: [@MDylan95](https://github.com/MDylan95)
- Repository: [sma_trafic](https://github.com/MDylan95/sma_trafic)

---

**Note**: Ce projet a été développé dans le cadre d'un projet académique sur les systèmes multi-agents appliqués à la régulation du trafic urbain à Abidjan, Côte d'Ivoire.

## 📚 Documentation Complète

- **[Mémoire Technique](MEMOIRE_TECHNIQUE_ARCHITECTURE_SMA.md)** - Justification des choix d'architecture SMA (67 pages)
- **[Rapport de Conformité](RAPPORT_CONFORMITE_CAHIER_DES_CHARGES.md)** - Conformité au cahier des charges
- **[Documentation Scénarios](DOCUMENTATION_SCENARIOS_TEST.md)** - Guide des scénarios de test
- **[Optimisations Performance](OPTIMISATIONS_PERFORMANCE.md)** - Optimisations appliquées (62% amélioration)
- **[Guide PostgreSQL](POSTGRESQL_GUIDE.md)** - Configuration et utilisation de la base de données
- **[Guide de Test](TESTING_GUIDE.md)** - Procédures de test et validation

## 🎯 Résultats Clés

- ✅ **300+ véhicules** simultanés sur réseau OSM réel
- ✅ **0.3s/step** après optimisations (62% amélioration)
- ✅ **~5000 edges** du réseau routier d'Abidjan
- ✅ **Scénarios validés** : Rush hour, Incident Pont De Gaulle
- ✅ **KPIs en temps réel** sauvegardés dans PostgreSQL
- ✅ **Visualisation SUMO** synchronisée avec agents Mesa
