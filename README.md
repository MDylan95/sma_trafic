# Système Multi-Agent de Régulation du Trafic Urbain — Abidjan

Simulation multi-agent décentralisée du trafic urbain d'Abidjan (Côte d'Ivoire), basée sur l'architecture BDI, le réseau routier réel OpenStreetMap et SUMO pour la visualisation microscopique.

Projet académique répondant au cahier des charges : agents BDI, communication FIPA-ACL, Contract Net Protocol, Q-Learning / Max-Pressure, scénarios réels (heure de pointe Yopougon/Abobo → Plateau, incident Pont De Gaulle).

## Vue d'ensemble

| Composant | Détail |
|-----------|--------|
| **Framework SMA** | Mesa (Python) — architecture BDI |
| **Moteur de simulation** | SUMO + TraCI (127 707 edges, 162 feux) |
| **Réseau routier** | OpenStreetMap Abidjan — UTM zone 30 |
| **Communication** | FIPA-ACL : INFORM, REQUEST, PROPOSE, CNP |
| **Optimisation feux** | Q-Learning (Bellman) ou Max-Pressure (Varaiya 2013) |
| **Routage véhicules** | `traci.simulation.findRoute` (Dijkstra C++ SUMO) |
| **Base de données** | PostgreSQL — KPIs, messages, positions |
| **Scénarios** | Heure de pointe, Incident Pont De Gaulle |

## Structure du projet

```
sma_trafic/
├── agents/
│   ├── bdi_agent.py              # Classe de base BDI (croyances, désirs, intentions)
│   ├── vehicle_agent.py          # Agent Véhicule — perception, reroutage dynamique
│   ├── intersection_agent.py     # Agent Intersection — Q-Learning / Max-Pressure / onde verte
│   └── crisis_manager_agent.py   # Gestionnaire de Crise — CNP, vague verte, urgences
│
├── algorithms/
│   └── routing.py                # A*, Dijkstra, routage dynamique (grille Mesa)
│
├── communication/
│   └── fipa_message.py           # FIPAMessage, Performative, MessageRouter, CommunicationProtocol
│
├── environment/
│   └── traffic_model.py          # Modèle Mesa principal — orchestration, KPIs, DataCollector
│
├── scenarios/
│   ├── rush_hour.py              # Heure de pointe : Yopougon/Abobo → Plateau (GPS réels)
│   └── incident.py               # Incident Pont De Gaulle → redirection Pont HKB
│
├── sumo_integration/
│   ├── sumo_connector.py         # Connecteur TraCI Mesa ↔ SUMO (KD-Tree, cache disque)
│   ├── import_real_abidjan.py    # Génération du réseau SUMO depuis OSM
│   ├── real_network_constants.py # BBOX zones (Yopougon, Abobo, Plateau, Cocody), ponts
│   ├── road_names.py             # Mapping ID edge → nom de rue
│   ├── abidjan_real.sumocfg      # Configuration SUMO
│   ├── abidjan_real.net.xml      # Réseau SUMO généré (415 Mo, non versionné)
│   ├── abidjan_real.osm.xml      # Données OSM brutes (non versionnées)
│   ├── edge_kdtree_cache.pkl     # Cache KD-Tree edges (généré au 1er lancement)
│   ├── od_pairs_cache.pkl        # Cache paires O/D valides (généré au 1er lancement)
│   ├── vtypes.add.xml            # Types de véhicules SUMO
│   ├── gui_settings.xml          # Paramètres d'affichage SUMO-GUI
│   ├── additional_tls.add.xml    # Feux additionnels
│   └── routes_real.rou.xml       # Fichier routes (vide — routes gérées par TraCI)
│
├── utils/
│   └── database.py               # Gestion PostgreSQL (KPIs, messages FIPA, positions)
│
├── visualizations/
│   └── charts.py                 # Graphiques matplotlib/seaborn des KPIs
│
├── tests/
│   └── test_agents.py            # Tests unitaires agents BDI
│
├── main.py                       # Point d'entrée principal
├── config.yaml                   # Configuration simulation (véhicules, zones, algos)
├── setup_database.py             # Initialisation des tables PostgreSQL
└── requirements.txt              # Dépendances Python
```

## Installation

### Prérequis

- Python 3.10+
- [SUMO 1.15+](https://sumo.dlr.de/docs/Downloads.php) avec SUMO-GUI
- PostgreSQL 14+ (optionnel, pour la persistance des KPIs)

### Mise en place

```bash
# Cloner le dépôt
git clone https://github.com/MDylan95/sma_trafic.git
cd sma_trafic

# Environnement virtuel
python -m venv .venv

# Activation (Linux/Mac)
source .venv/bin/activate
# Activation (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Dépendances Python
pip install -r requirements.txt
```

### SUMO

```bash
# Linux/Debian
sudo apt-get install sumo sumo-tools sumo-gui
export SUMO_HOME=/usr/share/sumo

# Windows : installer depuis https://sumo.dlr.de/docs/Downloads.php
# Puis ajouter C:\Program Files (x86)\Eclipse\Sumo\bin au PATH
```

### Réseau SUMO (si `abidjan_real.net.xml` absent)

```bash
python sumo_integration/import_real_abidjan.py
```

> Le réseau fait ~415 Mo. Les caches `edge_kdtree_cache.pkl` et `od_pairs_cache.pkl` sont générés automatiquement au premier lancement (~3 min). Les lancements suivants démarrent en ~1 min.

### Base de données (optionnel)

```bash
python setup_database.py
```

## Utilisation

```bash
# Windows — lancement recommandé
$env:PYTHONIOENCODING="utf-8"
python main.py --sumo --scenario rush_hour --steps 500

# Scénario heure de pointe avec SUMO-GUI
python main.py --sumo --scenario rush_hour --steps 1000

# Scénario incident Pont De Gaulle
python main.py --sumo --scenario incident --steps 1800

# Sans SUMO (Mesa seul, rapide)
python main.py --steps 500

# Tests rapides
python main.py --test
```

### Options principales

| Option | Description |
|--------|-------------|
| `--sumo` | Activer SUMO-GUI |
| `--sumo-delay N` | Délai affichage en ms (`0` = max vitesse, `100` = lisible) |
| `--scenario S` | `rush_hour`, `incident`, `normal`, `all` |
| `--steps N` | Nombre de pas de simulation (1 pas = 2s simulées) |
| `--log-level L` | `DEBUG`, `INFO`, `WARNING` |
| `--seed N` | Graine aléatoire pour reproductibilité |
| `--test` | Mode test rapide (50 steps, logs DEBUG) |

## Agents BDI

### Agent Véhicule (`vehicle_agent.py`)
- **Perception** : position actuelle, destination, congestion environnante (messages FIPA INFORM)
- **Actions** : déplacement, reroutage dynamique si congestion détectée
- **Types** : `standard`, `ambulance`, `bus_sotra`, `pompier`, `police`

### Agent Intersection (`intersection_agent.py`)
- **Perception** : files d'attente par direction (capteurs virtuels), états des voisins
- **Actions** : modification des phases de feux, diffusion d'état aux voisins
- **Optimisation** : Q-Learning (epsilon-greedy, équation de Bellman) ou Max-Pressure (Varaiya 2013)
- **Coordination** : onde verte inter-intersections via messages FIPA INFORM

### Gestionnaire de Crise (`crisis_manager_agent.py`)
- Détecte les congestions et incidents
- Force des vagues vertes pour ambulances et bus SOTRA
- Délègue la gestion de priorité via le **Contract Net Protocol** (CFP → PROPOSE → ACCEPT/REJECT)

## Communication FIPA-ACL

Tous les échanges inter-agents utilisent `FIPAMessage` défini dans `communication/fipa_message.py` :

| Performatif | Utilisation |
|-------------|-------------|
| `INFORM` | Diffusion congestion, état intersection voisine |
| `REQUEST` | Demande de priorité urgence, appel d'offres CNP |
| `PROPOSE` | Réponse à un CFP (Contract Net Protocol) |
| `ACCEPT-PROPOSAL` | Acceptation d'une proposition CNP |
| `REJECT-PROPOSAL` | Rejet d'une proposition CNP |
| `QUERY-REF` | Requête d'information sur l'état d'une intersection |

## Scénarios

### Heure de pointe (`rush_hour`)
Flux matinal depuis Yopougon et Abobo vers le Plateau. Les véhicules sont injectés dans SUMO avec des coordonnées GPS réelles tirées aléatoirement dans les bounding boxes des zones, converties en edges SUMO via TraCI.

### Incident Pont De Gaulle (`incident`)
Blocage du Pont De Gaulle à t=300s → l'Agent Gestionnaire de Crise notifie les intersections, force la redirection vers le Pont HKB. Mesure de l'impact sur les temps de trajet.

## Réseau SUMO

Généré depuis OpenStreetMap via `import_real_abidjan.py` :

- **Couverture** : lon [-4.080, -3.900] × lat [5.295, 5.480]
- **127 707 edges**, **162 feux de circulation**
- **Projection** : UTM zone 30N (WGS84), netOffset extrait du `.net.xml`
- **Zones géographiques** : Yopougon, Abobo, Plateau, Cocody

### Optimisation du démarrage (caches disque)

Au premier lancement, deux caches sont générés automatiquement :

| Fichier | Contenu | Temps génération | Temps chargement |
|---------|---------|-----------------|-----------------|
| `edge_kdtree_cache.pkl` | KD-Tree des 127 707 edges (midpoints) | ~38s | ~1s |
| `od_pairs_cache.pkl` | 200 paires O/D valides pré-calculées | ~90s | ~0.1s |

> Pour forcer la reconstruction (si le réseau change), supprimer ces deux fichiers `.pkl`.

## KPIs

Collectés à chaque pas et sauvegardés dans PostgreSQL (`kpis_timeseries`) :

| Indicateur | Calcul |
|------------|--------|
| Temps de trajet moyen | Moyenne sur les véhicules actifs |
| Longueur moyenne des files | Somme des queues / nb intersections |
| Vitesse moyenne | Moyenne sur les véhicules actifs |
| Niveau de congestion | `1 - (vitesse_moy / vitesse_max)` |
| Messages FIPA échangés | Compteur global `MessageRouter` |

## Tests

```bash
pytest tests/
pytest tests/ --cov=. --cov-report=html
```

## Configuration

Éditer `config.yaml` pour ajuster les paramètres principaux :

```yaml
simulation:
  num_vehicles: 300       # Nombre de véhicules initiaux
  duration: 3600          # Durée simulée en secondes

algorithms:
  routing:
    algorithm: A_STAR     # A_STAR ou DIJKSTRA
  traffic_light:
    algorithm: Q_LEARNING # Q_LEARNING ou MAX_PRESSURE
```

## Auteur

**Mac-Dylan KACOU, BOKA Agny-Blé Romaric** — [@MDylan95](https://github.com/MDylan95) — macdylankacou2000@gmail.com

---

*Projet académique — Systèmes multi-agents appliqués à la régulation du trafic urbain, Abidjan, Côte d'Ivoire.*
