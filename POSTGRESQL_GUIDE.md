# 🗄️ Guide PostgreSQL - Système Multi-Agent de Trafic

## 📋 Vue d'Ensemble

Le projet utilise PostgreSQL pour stocker et analyser toutes les données de simulation:
- Historique des simulations
- Statistiques des véhicules
- Performance des intersections
- KPIs en temps réel
- Messages FIPA échangés
- Positions des véhicules (pour replay)

---

## 🚀 Installation PostgreSQL

### Sur Ubuntu/Debian
```bash
# Installer PostgreSQL
sudo apt update
sudo apt install postgresql postgresql-contrib

# Démarrer le service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Vérifier le statut
sudo systemctl status postgresql
```

### Sur macOS
```bash
# Avec Homebrew
brew install postgresql

# Démarrer le service
brew services start postgresql
```

### Sur Windows
1. Télécharger depuis https://www.postgresql.org/download/windows/
2. Exécuter l'installateur
3. Suivre les instructions

---

## ⚙️ Configuration du Projet

### 1. Créer un utilisateur PostgreSQL (optionnel)

```bash
# Se connecter à PostgreSQL
sudo -u postgres psql

# Créer un utilisateur
CREATE USER traffic_user WITH PASSWORD 'votre_mot_de_passe';

# Donner les droits
ALTER USER traffic_user CREATEDB;

# Quitter
\q
```

### 2. Modifier config.yaml

```yaml
database:
  type: "postgresql"  # Utiliser PostgreSQL (au lieu de mongodb)
  
  postgresql:
    host: "localhost"
    port: 5432
    database: "traffic_sma"
    user: "postgres"           # ou traffic_user
    password: "password"       # CHANGEZ CE MOT DE PASSE!
```

⚠️ **IMPORTANT**: Changez le mot de passe par défaut!

### 3. Configurer la base de données

```bash
# Exécuter le script de configuration
python setup_database.py
```

Ce script va:
- ✅ Créer la base de données `traffic_sma`
- ✅ Créer toutes les tables nécessaires
- ✅ Créer les index pour les performances
- ✅ Tester la connexion

---

## 📊 Structure de la Base de Données

### Tables Principales

#### 1. `simulations`
Stocke les informations générales de chaque simulation.

```sql
CREATE TABLE simulations (
    simulation_id SERIAL PRIMARY KEY,
    simulation_name VARCHAR(255),
    scenario VARCHAR(100),
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    duration_seconds INTEGER,
    num_vehicles INTEGER,
    num_intersections INTEGER,
    algorithm_routing VARCHAR(50),
    algorithm_traffic_light VARCHAR(50),
    config JSONB,
    status VARCHAR(50)
);
```

#### 2. `vehicles`
Données de chaque véhicule.

```sql
CREATE TABLE vehicles (
    vehicle_id SERIAL PRIMARY KEY,
    simulation_id INTEGER REFERENCES simulations,
    vehicle_unique_id VARCHAR(100),
    origin_x FLOAT,
    origin_y FLOAT,
    destination_x FLOAT,
    destination_y FLOAT,
    total_travel_time FLOAT,
    distance_traveled FLOAT,
    average_speed FLOAT,
    route_changes INTEGER,
    reached_destination BOOLEAN
);
```

#### 3. `intersections`
Performance des intersections.

```sql
CREATE TABLE intersections (
    intersection_id SERIAL PRIMARY KEY,
    simulation_id INTEGER REFERENCES simulations,
    intersection_unique_id VARCHAR(100),
    position_x FLOAT,
    position_y FLOAT,
    total_vehicles_processed INTEGER,
    average_waiting_time FLOAT,
    phase_changes INTEGER,
    coordination_messages INTEGER
);
```

#### 4. `kpis_timeseries`
Évolution des KPIs dans le temps.

```sql
CREATE TABLE kpis_timeseries (
    kpi_id SERIAL PRIMARY KEY,
    simulation_id INTEGER REFERENCES simulations,
    step INTEGER,
    timestamp TIMESTAMP,
    average_travel_time FLOAT,
    average_queue_length FLOAT,
    total_messages INTEGER,
    active_vehicles INTEGER,
    congestion_level FLOAT
);
```

#### 5. `fipa_messages`
Historique des communications.

```sql
CREATE TABLE fipa_messages (
    message_id SERIAL PRIMARY KEY,
    simulation_id INTEGER REFERENCES simulations,
    sender VARCHAR(100),
    receiver VARCHAR(100),
    performative VARCHAR(50),
    content JSONB,
    protocol VARCHAR(100)
);
```

---

## 🎮 Utilisation

### Lancer une Simulation avec Sauvegarde

```bash
# Simulation standard
python main.py

# Les données seront automatiquement sauvegardées dans PostgreSQL!
```

### Analyser les Résultats

```bash
# Lancer l'outil d'analyse interactif
python analyze_database.py
```

Menu disponible:
```
1. Lister toutes les simulations
2. Détails d'une simulation
3. Visualiser l'évolution des KPIs
4. Comparer plusieurs simulations
5. Exporter en CSV
```

---

## 📈 Requêtes SQL Utiles

### Lister toutes les simulations
```sql
SELECT 
    simulation_id,
    simulation_name,
    scenario,
    num_vehicles,
    algorithm_routing,
    algorithm_traffic_light,
    status,
    start_time
FROM simulations
ORDER BY start_time DESC;
```

### Statistiques d'une simulation
```sql
SELECT 
    COUNT(*) as total_vehicles,
    COUNT(*) FILTER (WHERE reached_destination) as arrived,
    AVG(total_travel_time) as avg_travel_time,
    AVG(average_speed) as avg_speed,
    AVG(route_changes) as avg_route_changes
FROM vehicles
WHERE simulation_id = 1;  -- Remplacez par votre ID
```

### Évolution de la congestion
```sql
SELECT 
    step,
    congestion_level * 100 as congestion_pct,
    average_speed * 3.6 as speed_kmh,
    active_vehicles
FROM kpis_timeseries
WHERE simulation_id = 1
ORDER BY step;
```

### Comparer deux algorithmes
```sql
SELECT 
    s.algorithm_traffic_light,
    AVG(v.total_travel_time) as avg_time,
    AVG(k.congestion_level) as avg_congestion
FROM simulations s
JOIN vehicles v ON s.simulation_id = v.simulation_id
JOIN kpis_timeseries k ON s.simulation_id = k.simulation_id
WHERE s.scenario = 'rush_hour'
GROUP BY s.algorithm_traffic_light;
```

### Performance par intersection
```sql
SELECT 
    intersection_unique_id,
    position_x,
    position_y,
    average_waiting_time,
    phase_changes,
    coordination_messages
FROM intersections
WHERE simulation_id = 1
ORDER BY average_waiting_time DESC;
```

### Analyse des messages FIPA
```sql
SELECT 
    performative,
    COUNT(*) as count,
    COUNT(DISTINCT sender) as unique_senders
FROM fipa_messages
WHERE simulation_id = 1
GROUP BY performative
ORDER BY count DESC;
```

---

## 🔍 Analyses Avancées

### Créer une Vue pour Analyse Rapide
```sql
CREATE VIEW simulation_summary AS
SELECT 
    s.simulation_id,
    s.simulation_name,
    s.scenario,
    s.algorithm_routing,
    s.algorithm_traffic_light,
    COUNT(DISTINCT v.vehicle_id) as total_vehicles,
    AVG(v.total_travel_time) as avg_travel_time,
    AVG(v.average_speed) * 3.6 as avg_speed_kmh,
    AVG(i.average_waiting_time) as avg_waiting_time
FROM simulations s
LEFT JOIN vehicles v ON s.simulation_id = v.simulation_id
LEFT JOIN intersections i ON s.simulation_id = i.simulation_id
GROUP BY s.simulation_id;
```

Utilisation:
```sql
SELECT * FROM simulation_summary 
ORDER BY avg_travel_time;
```

### Export vers CSV
```sql
-- Depuis psql
\copy (SELECT * FROM vehicles WHERE simulation_id = 1) TO 'vehicles.csv' CSV HEADER;
```

---

## 🛠️ Maintenance

### Nettoyer les Vieilles Simulations
```sql
-- Supprimer les simulations de test
DELETE FROM simulations 
WHERE simulation_name LIKE '%Test%';

-- Supprimer les simulations de plus de 30 jours
DELETE FROM simulations 
WHERE start_time < NOW() - INTERVAL '30 days';
```

### Optimiser la Base
```sql
-- Analyser et mettre à jour les statistiques
ANALYZE;

-- Réorganiser les tables
VACUUM FULL;
```

### Vérifier la Taille
```sql
-- Taille de la base de données
SELECT pg_size_pretty(pg_database_size('traffic_sma'));

-- Taille par table
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## 🔐 Sécurité

### Bonnes Pratiques

1. **Mot de passe fort**
```yaml
password: "Tr@ff1c_Syst3m_2024!"  # Exemple
```

2. **Créer un utilisateur dédié**
```sql
CREATE USER traffic_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE traffic_sma TO traffic_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO traffic_app;
```

3. **Limiter les connexions**
Éditer `/etc/postgresql/*/main/pg_hba.conf`:
```
# Autoriser seulement localhost
host    traffic_sma    traffic_user    127.0.0.1/32    md5
```

---

## 🐛 Dépannage

### Erreur: "connection refused"
```bash
# Vérifier que PostgreSQL est démarré
sudo systemctl status postgresql

# Démarrer si nécessaire
sudo systemctl start postgresql
```

### Erreur: "authentication failed"
```bash
# Réinitialiser le mot de passe
sudo -u postgres psql
ALTER USER postgres PASSWORD 'nouveau_mot_de_passe';
```

### Erreur: "database does not exist"
```bash
# Créer manuellement
sudo -u postgres createdb traffic_sma
```

### Vérifier les connexions actives
```sql
SELECT * FROM pg_stat_activity 
WHERE datname = 'traffic_sma';
```

---

## 📚 Ressources

- **Documentation PostgreSQL**: https://www.postgresql.org/docs/
- **pgAdmin** (interface graphique): https://www.pgadmin.org/
- **DBeaver** (alternative): https://dbeaver.io/

---

## ✨ Exemples d'Analyse

### Comparer Q-Learning vs Max-Pressure

```python
from analyze_database import SimulationAnalyzer

analyzer = SimulationAnalyzer()

# Supposons que les simulations 1 et 2 utilisent des algorithmes différents
analyzer.compare_simulations_plot([1, 2], save_path="comparison.png")
```

### Export pour Excel
```python
analyzer = SimulationAnalyzer()
analyzer.export_to_csv(simulation_id=1, output_dir="exports")
# Ouvrir ensuite les CSV dans Excel pour analyse
```

---

**💡 Conseil**: Utilisez `analyze_database.py` pour la majorité des analyses. C'est plus simple que d'écrire du SQL!

**🎯 Objectif**: PostgreSQL vous permet d'analyser finement vos simulations et de comparer les performances des différents algorithmes sur le long terme.
