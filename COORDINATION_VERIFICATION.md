# Vérification de la Cohérence des Coordonnées

Ce document détaille la correspondance entre les systèmes de coordonnées Mesa et SUMO.

---

## 📐 Systèmes de Coordonnées

### Mesa (Simulation Multi-Agent)
- **Dimensions** : 5000m × 5000m (défini dans `config.yaml`)
- **Grille** : 6×6 intersections
- **Espacement** : `width // 5 = 1000m` (calculé dans `traffic_model.py` ligne 176)
- **Positions des nœuds** : 
  - X : 0, 1000, 2000, 3000, 4000 (5 valeurs car `range(0, 5000, 1000)`)
  - Y : 0, 1000, 2000, 3000, 4000

**⚠️ ATTENTION** : `range(0, 5000, 1000)` génère seulement 5 intersections par axe, pas 6 !
- Résultat : 5×5 = **25 intersections** au lieu de 36

### SUMO (Visualisation)
- **Dimensions** : 2500m × 2500m
- **Grille** : 6×6 intersections
- **Espacement** : 500m (défini dans `generate_network.py` ligne 324)
- **Positions des nœuds** :
  - X : 0, 500, 1000, 1500, 2000, 2500
  - Y : 0, 500, 1000, 1500, 2000, 2500

---

## 🌉 Mapping des Ponts

### Pont De Gaulle

| Système | Colonne | Position X | Edges Verticaux |
|---------|---------|------------|-----------------|
| **Mesa** | 2 | 2000m | Entre nœuds (2000, y) |
| **SUMO** | 2 | 1000m | `e_n{r}_2_to_n{r+1}_2` |

**Configuration actuelle** (`config.yaml` ligne 106) :
```yaml
blocked_road:
  name: "Pont De Gaulle"
  coordinates: [[2000, 0], [2000, 4000]]
```
✅ **CORRECT** pour Mesa (colonne 2 = x=2000)

**Visualisation SUMO** (`sumo_connector.py` ligne 634) :
```python
bridge_col = 2  # Colonne 2 en SUMO = x = 2*500 = 1000m
```
✅ **CORRECT** pour SUMO

### Pont HKB

| Système | Colonne | Position X |
|---------|---------|------------|
| **Mesa** | 3 | 3000m |
| **SUMO** | 3 | 1500m |

**Configuration actuelle** (`config.yaml` ligne 108) :
```yaml
alternative_road:
  name: "Pont HKB"
  coordinates: [[3000, 0], [3000, 4000]]
```
✅ **CORRECT** pour Mesa (colonne 3 = x=3000)

---

## 🔍 Problème Identifié : Nombre d'Intersections

### Code Actuel (`traffic_model.py` ligne 176-180)
```python
intersection_spacing = self.width // 5  # = 1000
for x in range(0, self.width, intersection_spacing):  # range(0, 5000, 1000)
    for y in range(0, self.height, intersection_spacing):
```

**Résultat** : `range(0, 5000, 1000)` = [0, 1000, 2000, 3000, 4000] → **5 valeurs**
- Grille : 5×5 = **25 intersections**

### Attendu (pour 6×6 = 36 intersections)
```python
intersection_spacing = self.width // 5  # = 1000
for x in range(0, self.width + 1, intersection_spacing):  # range(0, 5001, 1000)
    for y in range(0, self.height + 1, intersection_spacing):
```

**Résultat** : `range(0, 5001, 1000)` = [0, 1000, 2000, 3000, 4000, 5000] → **6 valeurs**
- Grille : 6×6 = **36 intersections**

---

## ✅ Vérifications de Cohérence

### 1. Noms des Rues (`generate_network.py` lignes 60-73)

```python
if c1 == 2:
    return f"Pont De Gaulle {direction}"
elif c1 == 3:
    return f"Pont HKB {direction}"
elif c1 == 0:
    return f"Rue Yopougon {direction}"
elif c1 == 1:
    return f"Rue Adjame {direction}"
```

✅ **CORRECT** : Colonne 2 = Pont De Gaulle

### 2. Blocage dans SUMO (`sumo_connector.py` lignes 659-663)

```python
bridge_edge_ids = []
for r in range(rows - 1):  # rows = 6, donc r = 0 à 4
    bridge_edge_ids.append(f"e_n{r}_{bridge_col}_to_n{r+1}_{bridge_col}")
    bridge_edge_ids.append(f"e_n{r+1}_{bridge_col}_to_n{r}_{bridge_col}")
```

**Edges générés** (pour `bridge_col=2`) :
- `e_n0_2_to_n1_2`, `e_n1_2_to_n0_2`
- `e_n1_2_to_n2_2`, `e_n2_2_to_n1_2`
- `e_n2_2_to_n3_2`, `e_n3_2_to_n2_2`
- `e_n3_2_to_n4_2`, `e_n4_2_to_n3_2`
- `e_n4_2_to_n5_2`, `e_n5_2_to_n4_2`

✅ **CORRECT** : Toutes les arêtes verticales de la colonne 2 sont bloquées

### 3. Blocage dans Mesa (`incident.py` lignes 114-122)

```python
network = self.model.road_network
start_node = network.get_nearest_node(tuple(start_coord))  # (2000, 0)
end_node = network.get_nearest_node(tuple(end_coord))      # (2000, 4000)

if start_node and end_node:
    self._block_path_between(start_node.id, end_node.id)
```

✅ **CORRECT** : Bloque les nœuds Mesa à x=2000

---

## 🎯 Conclusion

### Points Validés ✅
1. Les coordonnées du Pont De Gaulle dans `config.yaml` sont correctes pour Mesa (x=2000)
2. Le mapping SUMO utilise correctement `bridge_col=2` (x=1000 en SUMO)
3. Les noms des rues correspondent aux bonnes colonnes
4. Le blocage SUMO cible les bonnes arêtes
5. Le blocage est maintenu à chaque `sync_step` (correction appliquée)

### Point d'Attention ⚠️
- **Nombre d'intersections** : Le code génère actuellement 25 intersections (5×5) au lieu de 36 (6×6)
- **Impact** : Pas de nœud à x=5000 et y=5000. La dernière colonne/rangée manque.
- **Gravité** : Mineur pour le test de l'incident (le Pont De Gaulle est à x=2000, bien présent)

### Recommandation
Pour avoir exactement 36 intersections comme dans SUMO, modifier `traffic_model.py` ligne 179-180 :
```python
for x in range(0, self.width + 1, intersection_spacing):
    for y in range(0, self.height + 1, intersection_spacing):
```

---

## 📊 Tableau de Correspondance Finale

| Élément | Mesa (5000×5000) | SUMO (2500×2500) | Statut |
|---------|------------------|------------------|--------|
| Grille | 5×5 (actuellement) | 6×6 | ⚠️ Incohérent |
| Espacement | 1000m | 500m | ✅ Cohérent (ratio 2:1) |
| Pont De Gaulle | Col 2, x=2000 | Col 2, x=1000 | ✅ Cohérent |
| Pont HKB | Col 3, x=3000 | Col 3, x=1500 | ✅ Cohérent |
| Blocage incident | Edges à x=2000 | Edges à x=1000 | ✅ Cohérent |
| Maintien blocage | À chaque step | À chaque step | ✅ Corrigé |

---

**Date de vérification** : 23 février 2026
**Statut global** : ✅ Cohérent pour le test de l'incident
