# Checklist de Validation Pré-Test

Utilisez cette checklist pour vous assurer que l'environnement est correctement configuré avant de lancer la simulation.

---

## ✅ 1. Vérification Automatique

Lancez d'abord le script de test automatisé :

```bash
python test_suite.py
```

Ce script vérifie :
- ✓ Structure des fichiers
- ✓ Configuration YAML
- ✓ Imports Python
- ✓ Réseau SUMO
- ✓ Base de données PostgreSQL
- ✓ Cohérence du code

**Si tous les tests passent**, vous pouvez passer à l'étape 2.

**Si des tests échouent**, corrigez les erreurs indiquées avant de continuer.

---

## ✅ 2. Vérifications Manuelles

### 2.1. PostgreSQL

- [ ] Le service PostgreSQL est démarré
- [ ] La base de données `traffic_sma` existe
- [ ] Les tables ont été créées avec `python setup_database.py`
- [ ] Les identifiants dans `config.yaml` sont corrects

### 2.2. SUMO

- [ ] SUMO est installé et `SUMO_HOME` est défini dans les variables d'environnement
- [ ] Le réseau SUMO a été généré avec `python sumo_integration/generate_network.py`
- [ ] Les fichiers suivants existent dans `sumo_integration/` :
  - `abidjan.net.xml`
  - `abidjan.sumocfg`
  - `routes.rou.xml`
  - `vtypes.add.xml`

### 2.3. Dépendances Python

- [ ] L'environnement virtuel est activé (`.venv`)
- [ ] Toutes les dépendances sont installées : `pip install -r requirements.txt`

---

## ✅ 3. Vérification des Coordonnées (Critique)

### Grille Mesa vs SUMO

**Mesa** : Grille 5000×5000m, 6×6 intersections, espacement = 1000m
- Nœuds à : x/y = 0, 1000, 2000, 3000, 4000, 5000

**SUMO** : Grille 2500×2500m, 6×6 intersections, espacement = 500m
- Nœuds à : x/y = 0, 500, 1000, 1500, 2000, 2500

### Pont De Gaulle

**Dans Mesa** (colonne 2) :
- Coordonnées : `x = 2000`, `y = 0 à 4000`
- Vérifier dans `config.yaml` ligne 106 : `coordinates: [[2000, 0], [2000, 4000]]`

**Dans SUMO** (colonne 2) :
- Coordonnées : `x = 1000`, `y = 0 à 2500`
- Edges : `e_n0_2_to_n1_2`, `e_n1_2_to_n2_2`, ..., `e_n4_2_to_n5_2` (et inverses)

**Vérification** :
- [ ] `config.yaml` : `blocked_road.coordinates = [[2000, 0], [2000, 4000]]`
- [ ] `sumo_connector.py` ligne 634 : `bridge_col = 2`
- [ ] `generate_network.py` ligne 60-61 : `if c1 == 2: return "Pont De Gaulle ..."`

---

## ✅ 4. Test de Lancement Rapide

Avant de lancer une simulation complète, testez avec un nombre réduit de steps :

```bash
python main.py --sumo --sumo-interactive --steps 100
```

**Vérifiez** :
- [ ] SUMO-GUI s'ouvre sans erreur
- [ ] Les véhicules (points bleus) apparaissent et se déplacent
- [ ] Les feux de circulation (carrés rouges) changent de couleur
- [ ] Aucune erreur Python dans la console

---

## ✅ 5. Test de l'Incident

Lancez une simulation avec l'incident :

```bash
python main.py --sumo --sumo-interactive --scenario incident --steps 500
```

**À observer** :
- [ ] **À t=300s (step 300)** : Message `🚨 INCIDENT DÉCLENCHÉ : Pont De Gaulle`
- [ ] **Dans SUMO-GUI** : Le Pont De Gaulle (colonne verticale au centre-gauche, `x=1000` en SUMO) se colore en **rouge semi-transparent**
- [ ] **Blocage physique** : Les véhicules s'arrêtent et ne peuvent plus traverser le pont
- [ ] **Redirection** : Les véhicules recalculent leur route vers le Pont HKB (colonne suivante, `x=1500` en SUMO)
- [ ] **À t=420s (step 420)** : Message `✅ INCIDENT RÉSOLU`, le rouge disparaît, le trafic reprend

---

## ✅ 6. Validation des Résultats

Après une simulation complète :

### 6.1. Fichiers générés

- [ ] `data/results/kpis.png` : Graphiques des KPIs
- [ ] `data/results/summary.png` : Résumé de la simulation
- [ ] `data/results/network.png` : Carte du réseau
- [ ] `data/results/heatmap.png` : Carte de chaleur du trafic

### 6.2. Base de données

Connectez-vous à PostgreSQL et vérifiez :

```sql
-- Lister les simulations
SELECT simulation_id, scenario, start_time FROM simulations ORDER BY start_time DESC LIMIT 5;

-- Vérifier les KPIs
SELECT step, kpi_name, kpi_value FROM kpis_timeseries 
WHERE simulation_id = 'VOTRE_SIM_ID' AND kpi_name = 'Average_Travel_Time' 
ORDER BY step LIMIT 10;
```

- [ ] Une nouvelle entrée existe dans `simulations`
- [ ] Des données existent dans `kpis_timeseries`
- [ ] Des véhicules sont enregistrés dans `vehicles`

---

## 🚨 Problèmes Courants

### Erreur : `KeyError: 'level'`
**Cause** : Incohérence dans la structure des messages de congestion.
**Solution** : Vérifiée et corrigée dans `intersection_agent.py` ligne 217 et 703.

### Erreur : Mauvaise route bloquée (Rue Adjamé au lieu du Pont De Gaulle)
**Cause** : Coordonnées incorrectes dans `config.yaml`.
**Solution** : Vérifiée et corrigée. Le Pont De Gaulle est à `x=2000` en Mesa.

### Blocage non permanent (véhicules continuent à circuler)
**Cause** : `setMaxSpeed(0)` n'était appelé qu'une fois.
**Solution** : Corrigée. Le blocage est maintenant ré-appliqué à chaque `sync_step`.

### SUMO-GUI ne s'ouvre pas
**Cause** : `SUMO_HOME` non défini ou SUMO non installé.
**Solution** : 
```bash
# Windows
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo
# Linux/Mac
export SUMO_HOME=/usr/share/sumo
```

### Erreur de connexion PostgreSQL
**Cause** : Service non démarré ou identifiants incorrects.
**Solution** : Vérifiez `config.yaml` et démarrez PostgreSQL.

---

## 📊 Métriques de Succès

Une simulation réussie doit montrer :

1. **Temps de trajet moyen** : Augmente pendant l'incident, puis redescend après résolution
2. **Niveau de congestion** : Pic pendant l'incident sur le Pont De Gaulle
3. **Messages échangés** : Augmentation lors de la détection et diffusion de l'incident
4. **Véhicules redirigés** : > 0 dans les statistiques du scénario incident
5. **Ondes vertes actives** : > 0 dans les métriques de coordination

---

## ✅ Validation Finale

Si tous les points ci-dessus sont validés, le projet est **prêt pour une démonstration complète**.

Lancez la simulation finale avec :

```bash
python main.py --sumo --sumo-interactive --steps 3000
```

Bonne simulation ! 🚗🚦
