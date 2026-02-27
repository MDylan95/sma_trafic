# 🗄️ INTÉGRATION POSTGRESQL - Récapitulatif

## ✅ Ce qui a été Ajouté

L'intégration PostgreSQL est maintenant **complète et fonctionnelle** dans votre projet !

---

## 📁 Nouveaux Fichiers Créés

### 1. `utils/database.py` (580 lignes)
**Module principal de gestion PostgreSQL**

Fonctionnalités:
- ✅ Pool de connexions pour performances optimales
- ✅ Création automatique de 7 tables
- ✅ Insertion des données de simulation
- ✅ Requêtes d'analyse et statistiques
- ✅ Comparaison de simulations
- ✅ Gestion des erreurs et logging

Classes principales:
```python
class PostgreSQLDatabase:
    - create_simulation()
    - insert_vehicle()
    - insert_vehicles_batch()
    - insert_intersection()
    - insert_kpi_snapshot()
    - insert_message()
    - get_simulation_statistics()
    - compare_simulations()
```

### 2. `setup_database.py` (150 lignes)
**Script de configuration initiale**

Usage:
```bash
python setup_database.py
```

Effectue:
- ✅ Création de la base de données `traffic_sma`
- ✅ Création de toutes les tables
- ✅ Création des index pour performances
- ✅ Test de connexion
- ✅ Insertion d'une simulation test

### 3. `analyze_database.py` (320 lignes)
**Outil d'analyse interactif**

Usage:
```bash
python analyze_database.py
```

Fonctionnalités:
- ✅ Lister toutes les simulations
- ✅ Afficher les détails d'une simulation
- ✅ Générer des graphiques d'évolution des KPIs
- ✅ Comparer plusieurs simulations
- ✅ Exporter en CSV

Menu interactif:
```
🔍 OPTIONS:
  1. Lister toutes les simulations
  2. Détails d'une simulation
  3. Visualiser l'évolution des KPIs
  4. Comparer plusieurs simulations
  5. Exporter en CSV
  0. Quitter
```

### 4. `POSTGRESQL_GUIDE.md` (450 lignes)
**Guide complet d'utilisation**

Contient:
- ✅ Installation de PostgreSQL
- ✅ Configuration du projet
- ✅ Structure détaillée des tables
- ✅ Requêtes SQL utiles
- ✅ Analyses avancées
- ✅ Maintenance et optimisation
- ✅ Sécurité
- ✅ Dépannage

---

## 🗂️ Structure de la Base de Données

### Tables Créées (7 au total)

#### 1. `simulations`
Informations générales sur chaque simulation
```sql
- simulation_id (PK)
- simulation_name
- scenario
- start_time, end_time
- num_vehicles, num_intersections
- algorithm_routing, algorithm_traffic_light
- config (JSONB)
- status
```

#### 2. `vehicles`
Données de chaque véhicule
```sql
- vehicle_id (PK)
- simulation_id (FK)
- origin_x, origin_y
- destination_x, destination_y
- total_travel_time
- distance_traveled
- average_speed
- route_changes
- reached_destination
```

#### 3. `intersections`
Performance des intersections
```sql
- intersection_id (PK)
- simulation_id (FK)
- position_x, position_y
- total_vehicles_processed
- average_waiting_time
- phase_changes
- coordination_messages
```

#### 4. `kpis_timeseries`
Évolution des KPIs dans le temps (sauvegardés toutes les 10 secondes)
```sql
- kpi_id (PK)
- simulation_id (FK)
- step
- timestamp
- average_travel_time
- average_queue_length
- total_messages
- active_vehicles
- congestion_level
```

#### 5. `fipa_messages`
Historique des communications entre agents
```sql
- message_id (PK)
- simulation_id (FK)
- sender, receiver
- performative
- content (JSONB)
- protocol
- timestamp
```

#### 6. `simulation_events`
Événements spéciaux pendant la simulation
```sql
- event_id (PK)
- simulation_id (FK)
- event_type
- event_data (JSONB)
- timestamp
```

#### 7. `vehicle_positions`
Positions des véhicules pour replay/animation
```sql
- position_id (PK)
- simulation_id (FK)
- vehicle_unique_id
- step
- position_x, position_y
- speed
- timestamp
```

### Index Créés
```sql
- idx_vehicles_simulation
- idx_kpis_simulation
- idx_messages_simulation
- idx_positions_simulation
```

---

## 🔄 Modifications du Code Existant

### `environment/traffic_model.py`
**Modifications apportées:**

1. **Import du module database**
```python
from utils.database import PostgreSQLDatabase
```

2. **Initialisation dans __init__()**
```python
self.use_database = config.get('database', {}).get('type') == 'postgresql'
self.db = None
self.simulation_id = None

if self.use_database:
    self.db = PostgreSQLDatabase(config_path)
    self.simulation_id = self.db.create_simulation(...)
```

3. **Sauvegarde à chaque step** (toutes les 10 secondes)
```python
if self.use_database and self.current_step % 10 == 0:
    self.db.insert_kpi_snapshot(self.simulation_id, self.current_step, kpis)
```

4. **Sauvegarde finale dans run_simulation()**
```python
# Sauvegarder tous les véhicules
self.db.insert_vehicles_batch(self.simulation_id, vehicles_data)

# Sauvegarder toutes les intersections
for intersection in self.intersections:
    self.db.insert_intersection(self.simulation_id, stats)

# Terminer la simulation
self.db.end_simulation(self.simulation_id, duration)
```

### `config.yaml`
**Section database déjà configurée:**
```yaml
database:
  type: "postgresql"  # Activé par défaut
  
  postgresql:
    host: "localhost"
    port: 5432
    database: "traffic_sma"
    user: "postgres"
    password: "password"  # À CHANGER!
```

### `requirements.txt`
**Dépendances ajoutées:**
```txt
psycopg2-binary==2.9.9  # Driver PostgreSQL
tabulate==0.9.0         # Pour affichage tableaux
```

---

## 🚀 Utilisation Complète

### Étape 1: Installation PostgreSQL

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Windows:**
Télécharger depuis https://www.postgresql.org/download/windows/

### Étape 2: Configuration

```bash
# Modifier le mot de passe dans config.yaml
nano config.yaml  # Changez "password"

# Configurer la base de données
python setup_database.py
```

Output attendu:
```
✅ Base de données 'traffic_sma' créée
✅ Tables créées avec succès
✅ Test réussi (simulation_id: 1)
✅ CONFIGURATION TERMINÉE AVEC SUCCÈS!
```

### Étape 3: Lancer une Simulation

```bash
# Simulation avec sauvegarde automatique
python main.py

# Ou simulation de test
python main.py --test
```

Les données seront automatiquement sauvegardées dans PostgreSQL !

### Étape 4: Analyser les Résultats

```bash
# Lancer l'analyseur interactif
python analyze_database.py
```

Ou directement en Python:
```python
from analyze_database import SimulationAnalyzer

analyzer = SimulationAnalyzer()

# Lister les simulations
analyzer.list_simulations()

# Détails d'une simulation
analyzer.show_simulation_details(1)

# Graphique d'évolution
analyzer.plot_kpis_evolution(1, save_path="kpis.png")

# Comparer 2 simulations
analyzer.compare_simulations_plot([1, 2])

# Export CSV
analyzer.export_to_csv(1)
```

---

## 📊 Exemples de Requêtes SQL

### Statistiques Basiques
```sql
-- Nombre de simulations
SELECT COUNT(*) FROM simulations;

-- Dernières simulations
SELECT simulation_id, simulation_name, start_time, status
FROM simulations
ORDER BY start_time DESC
LIMIT 5;
```

### Analyse de Performance
```sql
-- Temps de trajet moyen par simulation
SELECT 
    s.simulation_id,
    s.simulation_name,
    AVG(v.total_travel_time) as avg_time,
    COUNT(v.vehicle_id) as num_vehicles
FROM simulations s
JOIN vehicles v ON s.simulation_id = v.simulation_id
GROUP BY s.simulation_id
ORDER BY avg_time;
```

### Comparaison d'Algorithmes
```sql
-- Q-Learning vs Max-Pressure
SELECT 
    algorithm_traffic_light,
    AVG(avg_travel_time) as avg_time,
    AVG(avg_congestion) as avg_cong
FROM (
    SELECT 
        s.algorithm_traffic_light,
        AVG(k.average_travel_time) as avg_travel_time,
        AVG(k.congestion_level) as avg_congestion
    FROM simulations s
    JOIN kpis_timeseries k ON s.simulation_id = k.simulation_id
    GROUP BY s.simulation_id, s.algorithm_traffic_light
) sub
GROUP BY algorithm_traffic_light;
```

---

## 🎯 Avantages de PostgreSQL

### 1. **Persistance des Données**
- ✅ Toutes les simulations sont conservées
- ✅ Historique complet accessible
- ✅ Pas de perte de données entre exécutions

### 2. **Analyses Avancées**
- ✅ Comparaison de multiples simulations
- ✅ Requêtes SQL complexes
- ✅ Agrégations et statistiques
- ✅ Tendances sur le long terme

### 3. **Performance**
- ✅ Pool de connexions
- ✅ Index optimisés
- ✅ Insertion en batch
- ✅ Requêtes rapides

### 4. **Intégration**
- ✅ Export CSV facile
- ✅ Compatible avec Excel, Tableau, Power BI
- ✅ API d'analyse Python
- ✅ Visualisations intégrées

---

## 🔍 Cas d'Usage

### 1. Recherche Académique
```python
# Comparer 10 simulations avec différents paramètres
analyzer = SimulationAnalyzer()
results = analyzer.db.compare_simulations(list(range(1, 11)))

# Exporter pour analyse statistique (R, SPSS, etc.)
analyzer.export_to_csv(simulation_id, "research_data")
```

### 2. Optimisation de Paramètres
```sql
-- Trouver les meilleurs paramètres
SELECT 
    config->>'algorithms'->>'traffic_light'->>'learning_rate' as lr,
    AVG(congestion_level) as avg_congestion
FROM simulations s
JOIN kpis_timeseries k ON s.simulation_id = k.simulation_id
GROUP BY config->>'algorithms'->>'traffic_light'->>'learning_rate'
ORDER BY avg_congestion;
```

### 3. Validation de Scénarios
```python
# Comparer scénario rush_hour vs incident
rush_sims = [1, 2, 3]  # Simulations rush hour
incident_sims = [4, 5, 6]  # Simulations incident

analyzer.compare_simulations_plot(rush_sims + incident_sims)
```

---

## 📈 Métriques Stockées

### Par Simulation
- Temps total
- Nombre de véhicules
- Algorithmes utilisés
- Configuration complète (JSONB)

### Par Véhicule
- Temps de trajet
- Distance parcourue
- Vitesse moyenne
- Changements de route
- Arrivée à destination

### Par Intersection
- Véhicules traités
- Temps d'attente moyen
- Changements de phase
- Messages de coordination

### Série Temporelle (KPIs)
- Temps de trajet moyen
- Longueur des files
- Messages échangés
- Véhicules actifs
- Niveau de congestion

---

## 🛠️ Maintenance

### Backup Régulier
```bash
# Sauvegarder la base
pg_dump traffic_sma > backup_$(date +%Y%m%d).sql

# Restaurer
psql traffic_sma < backup_20240210.sql
```

### Nettoyage
```sql
-- Supprimer les simulations de test
DELETE FROM simulations WHERE simulation_name LIKE '%Test%';

-- Vacuum pour récupérer l'espace
VACUUM FULL;
```

### Monitoring
```sql
-- Taille de la base
SELECT pg_size_pretty(pg_database_size('traffic_sma'));

-- Nombre de lignes par table
SELECT 
    schemaname,
    tablename,
    n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;
```

---

## ✨ Prochaines Étapes Possibles

### Extensions Envisageables

1. **Dashboard Web**
   - Flask/Streamlit pour visualisation temps réel
   - Connexion directe à PostgreSQL
   - Graphiques interactifs

2. **API REST**
   - FastAPI pour exposer les données
   - Endpoints pour requêtes personnalisées
   - Authentification

3. **Machine Learning**
   - Export des données pour entraînement
   - Prédiction de congestion
   - Optimisation automatique

4. **Replay 3D**
   - Utiliser `vehicle_positions`
   - Animation 3D de la simulation
   - Export vidéo

---

## 📞 Support

### Problèmes Courants

**"psycopg2 import error"**
```bash
pip install psycopg2-binary --break-system-packages
```

**"connection refused"**
```bash
sudo systemctl start postgresql
```

**"authentication failed"**
```bash
# Vérifier config.yaml
# Réinitialiser le mot de passe si nécessaire
```

### Logs
```python
# Les erreurs PostgreSQL sont loggées dans:
data/logs/simulation_*.log
```

---

## 🎉 Conclusion

Votre projet dispose maintenant d'un **système de persistance professionnel** avec PostgreSQL !

**Avantages:**
- ✅ Historique complet des simulations
- ✅ Analyses avancées et comparaisons
- ✅ Export facile des données
- ✅ Performance optimale
- ✅ Prêt pour la recherche académique

**Prêt à utiliser:**
```bash
python setup_database.py  # Une seule fois
python main.py            # Simulation avec sauvegarde auto
python analyze_database.py  # Analyse interactive
```

🚀 **Votre système multi-agent est maintenant complet et production-ready !**
