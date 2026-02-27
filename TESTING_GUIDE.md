# Guide de Test Complet - Système Multi-Agent de Régulation du Trafic

Ce document fournit les instructions pour tester et valider toutes les fonctionnalités clés du projet.

---

## 1. Prérequis et Installation

Assurez-vous que l'environnement est correctement configuré avant de lancer les tests.

### 1.1. Logiciels

- **Python** : Version 3.9 ou supérieure.
- **SUMO** : Version 1.10.0 ou supérieure. Assurez-vous que le chemin vers le dossier `bin` de SUMO est ajouté à la variable d'environnement `SUMO_HOME`.
- **PostgreSQL** : Version 13 ou supérieure, avec une base de données nommée `traffic_sma`.

### 1.2. Bibliothèques Python

Installez toutes les dépendances via le fichier `requirements.txt` :

```bash
pip install -r requirements.txt
```

### 1.3. Base de Données

1.  Lancez le service PostgreSQL.
2.  Créez une base de données nommée `traffic_sma`.
3.  Exécutez le script `setup_database.py` pour créer les tables nécessaires :

    ```bash
    python setup_database.py
    ```

### 1.4. Fichiers de Configuration

- **`config.yaml`** : Vérifiez que les informations de connexion à la base de données sont correctes.
- **`sumo_integration/abidjan.sumocfg`** : Ce fichier doit exister. S'il est manquant, régénérez-le avec le script `generate_network.py` :

    ```bash
    python sumo_integration/generate_network.py
    ```

---

## 2. Plan de Test

Nous allons exécuter 4 tests principaux pour valider chaque aspect du système.

### Test 1 : Scénario de Base (Validation Générale)

**Objectif** : Vérifier que la simulation se lance, que les agents interagissent et que les données sont collectées sans erreur.

**Commande** :

```bash
python main.py --sumo --scenario default --steps 1000
```

**Ce qu'il faut observer** :

1.  **Console** : Pas de message d'erreur. La simulation doit progresser et afficher les `steps`.
2.  **SUMO-GUI** : Les véhicules (points bleus) se déplacent et s'arrêtent aux intersections (carrés rouges).
3.  **Dossier `data/results`** : Des graphiques (`kpis.png`, `summary.png`, etc.) doivent être générés à la fin.
4.  **Base de données** : Une nouvelle entrée doit apparaître dans la table `simulations`.

### Test 2 : Scénario Heure de Pointe

**Objectif** : Valider la capacité du système à gérer une forte charge de trafic et à observer les stratégies de régulation.

**Commande** :

```bash
python main.py --sumo --scenario rush_hour
```

**Ce qu'il faut observer** :

1.  **Console** : Le nombre de `Véhicules actifs` doit augmenter rapidement, atteindre un pic, puis diminuer.
2.  **SUMO-GUI** :
    - Une forte densité de véhicules doit être visible, en particulier sur les axes Yopougon/Abobo → Plateau.
    - Observez les files d'attente aux intersections. Les feux doivent s'adapter pour fluidifier les axes les plus chargés.
3.  **Graphiques (`kpis.png`)** :
    - `Longueur Moyenne des Files` et `Niveau de Congestion` doivent montrer une courbe en cloche, suivant le profil du scénario.
    - `Vitesse Moyenne` doit chuter pendant le pic de trafic.

### Test 3 : Scénario Incident sur le Pont De Gaulle

**Objectif** : Tester la résilience du système face à un blocage imprévu et la capacité des agents à se réadapter.

**Commande** :

```bash
python main.py --sumo --scenario incident
```

**Ce qu'il faut observer** :

1.  **Console** :
    - À `t=1800s` (step 1800), un message `🚨 INCIDENT DÉCLENCHÉ` doit apparaître.
    - À `t=2700s` (step 2700), un message `✅ INCIDENT RÉSOLU` doit apparaître.
2.  **SUMO-GUI** :
    - **À 1800s** : Le Pont De Gaulle (colonne `c=2`) doit se colorer en **rouge semi-transparent**. Les véhicules s'arrêtent et ne peuvent plus le traverser.
    - **Pendant l'incident** : Observez les véhicules qui approchent du pont. Ils doivent s'arrêter, puis recalculer leur itinéraire pour se diriger vers le Pont HKB (colonne `c=3`). Le trafic sur le Pont HKB doit augmenter significativement.
    - **À 2700s** : La couleur rouge disparaît, et le trafic reprend normalement sur le Pont De Gaulle.
3.  **Graphiques (`kpis.png`)** :
    - `Temps de Trajet Moyen` doit augmenter brusquement après le déclenchement de l'incident, puis se stabiliser à un niveau plus élevé, et enfin redescendre après la résolution.

### Test 4 : Comparaison des Algorithmes (Max-Pressure vs Q-Learning)

**Objectif** : Évaluer l'efficacité des deux algorithmes de gestion des feux.

**Procédure** :

1.  **Modifier `config.yaml`** : Mettez `algorithm` dans la section `traffic_light` à `MAX_PRESSURE`.
2.  **Lancer le test Max-Pressure** :

    ```bash
    python main.py --scenario rush_hour --output-dir data/results/max_pressure
    ```

3.  **Modifier `config.yaml`** : Mettez `algorithm` à `Q_LEARNING`.
4.  **Lancer le test Q-Learning** :

    ```bash
    python main.py --scenario rush_hour --output-dir data/results/q_learning
    ```

**Ce qu'il faut observer** :

1.  **Dossiers de résultats** : Comparez les fichiers `kpis.png` et `summary.png` dans `data/results/max_pressure` et `data/results/q_learning`.
2.  **Analyse attendue** :
    - **Q-Learning** devrait (après plusieurs simulations pour apprendre) montrer un `Temps de Trajet Moyen` et une `Longueur Moyenne des Files` légèrement inférieurs à Max-Pressure.
    - **Max-Pressure** est une heuristique très efficace. La différence peut être subtile, mais Q-Learning a le potentiel de trouver des stratégies de coordination plus complexes.

---

## 3. Analyse des Données en Base de Données

Utilisez un client PostgreSQL (comme DBeaver ou pgAdmin) pour explorer les résultats.

**Requêtes SQL utiles** :

- **Lister les simulations** :

  ```sql
  SELECT simulation_id, simulation_name, scenario, start_time, end_time FROM simulations ORDER BY start_time DESC;
  ```

- **Analyser les KPIs d'une simulation (remplacez `SIM_ID`)** :

  ```sql
  SELECT step, kpi_name, kpi_value FROM kpis_timeseries WHERE simulation_id = 'SIM_ID' AND kpi_name = 'Average_Travel_Time' ORDER BY step;
  ```

- **Analyser les messages FIPA échangés** :

  ```sql
  SELECT performative, protocol, COUNT(*) as count
  FROM fipa_messages
  WHERE simulation_id = 'SIM_ID'
  GROUP BY performative, protocol
  ORDER BY count DESC;
  ```

Ce guide vous permettra de valider de manière exhaustive le bon fonctionnement de chaque composant du projet.
