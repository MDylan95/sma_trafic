# Système Multi-Agent de Régulation du Trafic Urbain — Abidjan

Simulation multi-agent du trafic urbain d'Abidjan (Côte d'Ivoire) utilisant l'architecture BDI, le réseau routier réel OpenStreetMap (~40 000 edges, 82 feux) et SUMO pour la visualisation microscopique.

## Vue d'ensemble

Système décentralisé où des agents autonomes (véhicules, intersections, gestionnaire de crise) interagissent pour réguler le trafic.

- **Réseau routier réel** — OpenStreetMap d'Abidjan (39 923 edges, 82 feux de circulation)
- **Intégration SUMO** — Visualisation temps réel via TraCI, projection UTM zone 30
- **Architecture BDI** — Agents avec croyances, désirs, intentions
- **Communication FIPA-ACL** — Messages standardisés inter-agents
- **Scénarios** — Heure de pointe (Yopougon/Abobo → Plateau), incident (Pont De Gaulle)
- **PostgreSQL** — Stockage et analyse des KPIs

## Structure du projet

```
sma_trafic/
├── agents/                       # Agents BDI
│   ├── bdi_agent.py              # Classe de base BDI
│   ├── vehicle_agent.py          # Agent Véhicule
│   ├── intersection_agent.py     # Agent Intersection (Q-Learning / Max-Pressure)
│   └── crisis_manager_agent.py   # Gestionnaire de Crise
│
├── algorithms/
│   └── routing.py                # A*, Dijkstra, routage dynamique
│
├── communication/
│   └── fipa_message.py           # Messages FIPA-ACL + Contract Net Protocol
│
├── environment/
│   └── traffic_model.py          # Modèle Mesa principal
│
├── scenarios/
│   ├── rush_hour.py              # Heure de pointe Yopougon/Abobo → Plateau
│   └── incident.py               # Incident Pont De Gaulle → Pont HKB
│
├── sumo_integration/             # Intégration SUMO
│   ├── sumo_connector.py         # Connecteur TraCI Mesa ↔ SUMO
│   ├── import_real_abidjan.py    # Script d'import OSM → réseau SUMO
│   ├── real_network_constants.py # Constantes : ponts, zones géographiques (BBOX)
│   ├── road_names.py             # Noms des routes pour affichage
│   ├── abidjan_real.sumocfg      # Configuration SUMO
│   ├── abidjan_real.net.xml      # Réseau SUMO (généré, non versionné)
│   ├── abidjan_real.osm.xml      # Données OSM (généré, non versionné)
│   ├── vtypes.add.xml            # Types de véhicules
│   ├── gui_settings.xml          # Paramètres d'affichage SUMO-GUI
│   ├── additional_tls.add.xml    # Feux de circulation additionnels
│   └── routes_real.rou.xml       # Routes (vide, géré par TraCI)
│
├── utils/
│   └── database.py               # Gestion PostgreSQL
│
├── visualizations/
│   └── charts.py                 # Graphiques et statistiques
│
├── tests/
│   └── test_agents.py            # Tests unitaires
│
├── main.py                       # Point d'entrée
├── config.yaml                   # Configuration simulation
├── setup_database.py             # Initialisation PostgreSQL
└── requirements.txt              # Dépendances Python
```

## Installation

### Prérequis

- Python 3.10+
- SUMO 1.15+ (avec SUMO-GUI)
- PostgreSQL 14+ (optionnel)

### Mise en place

```bash
# Cloner et entrer dans le projet
git clone https://github.com/MDylan95/sma_trafic.git
cd sma_trafic

# Environnement virtuel
python -m venv .venv
source .venv/bin/activate   # Linux/Mac

# Dépendances Python
pip install -r requirements.txt

# SUMO (Ubuntu/Debian)
sudo apt-get install sumo sumo-tools sumo-gui
export SUMO_HOME=/usr/share/sumo

# Générer le réseau SUMO (si abidjan_real.net.xml n'existe pas)
python sumo_integration/import_real_abidjan.py

# PostgreSQL 
python setup_database.py
```

## Utilisation

```bash
# Simulation basique (sans SUMO)
python main.py --steps 500

# Avec SUMO-GUI interactif
python main.py --sumo --sumo-interactive --sumo-delay 100 --steps 1000

# Scénario heure de pointe
python main.py --sumo --sumo-interactive --scenario rush_hour --steps 1000

# Scénario incident Pont De Gaulle
python main.py --sumo --sumo-interactive --scenario incident --steps 1800

# Mode test rapide
python main.py --test
```

### Options principales

| Option | Description |
|--------|-------------|
| `--sumo` | Activer SUMO-GUI |
| `--sumo-interactive` | SUMO attend le clic sur Play |
| `--sumo-delay N` | Délai affichage en ms (100 = lent, 0 = rapide) |
| `--scenario S` | `rush_hour`, `incident`, `normal`, `all` |
| `--steps N` | Nombre de pas de simulation |
| `--verbose` | Logs détaillés (DEBUG) |
| `--seed N` | Seed pour reproductibilité |

## Agents

### Agent Véhicule
Représente un véhicule (standard, ambulance, bus SOTRA, pompier, police). Perçoit le trafic, calcule sa route via A*, s'arrête aux feux, évite les congestions.

### Agent Intersection
Gère un carrefour à feux. Optimise les durées vert/rouge via Q-Learning ou Max-Pressure. Se coordonne avec les voisins pour créer des ondes vertes.

### Gestionnaire de Crise
Supervise les véhicules d'urgence, force des vagues vertes, coordonne la réponse aux incidents via le Contract Net Protocol.

## Scénarios

### Heure de pointe
Flux matinal Yopougon/Abobo → Plateau avec coordonnées GPS réelles. Les véhicules sont injectés dans SUMO aux positions GPS correspondant aux zones d'origine définies dans `real_network_constants.py`.

### Incident Pont De Gaulle
Blocage du Pont De Gaulle après 300s → redirection automatique vers Pont HKB. Mesure du temps de réaction et de l'impact sur le trafic.

## Réseau SUMO

Le réseau est généré depuis OpenStreetMap via `import_real_abidjan.py` :

- **Couverture** : lon [-4.074, -3.924] × lat [5.283, 5.441]
- **39 923 edges**, **82 feux de circulation**
- **Projection** : UTM zone 30 (WGS84)
- **Zones** : Yopougon, Abobo, Plateau, Cocody

La conversion GPS → coordonnées SUMO utilise une projection UTM manuelle avec le `netOffset` du réseau, garantissant une correspondance exacte entre les coordonnées GPS des zones et les edges du réseau.

## KPIs

| Indicateur | Description |
|------------|-------------|
| Temps de trajet moyen | Σ(temps_trajet) / nb_véhicules |
| Longueur des files | Moyenne des véhicules en attente par intersection |
| Vitesse moyenne | Σ(vitesse) / nb_véhicules |
| Niveau de congestion | 1 - (vitesse_moy / vitesse_max) |
| Messages échangés | Total messages FIPA-ACL |

## Tests

```bash
pytest tests/
pytest tests/ --cov=. --cov-report=html
```

## Configuration

Éditer `config.yaml` pour ajuster :

```yaml
simulation:
  duration: 3600
  num_vehicles: 300

algorithms:
  routing:
    algorithm: A_STAR
  traffic_light:
    algorithm: Q_LEARNING
```

## Auteur

**Mac-Dylan KACOU** — [@MDylan95](https://github.com/MDylan95) — macdylankacou2000@gmail.com

---

Projet académique — Systèmes multi-agents appliqués à la régulation du trafic urbain, Abidjan, Côte d'Ivoire.
