# 🚦 La réalité de l'affichage des feux dans SUMO-GUI

## ⚠️ Important à comprendre

Dans SUMO-GUI en vue 2D, **il n'existe pas de "feux de circulation" visuels** comme des objets séparés (panneaux rouge/vert/jaune). Les feux sont représentés par :

### 1. **Link Rules** (rectangles colorés)
- Ce sont de **petits rectangles rouge/vert/jaune** qui apparaissent sur les **connexions internes** des jonctions
- Ils indiquent l'état du feu pour chaque direction
- Visibles uniquement avec `showLinkRules="1"` et `hideConnectors="0"`
- **Nécessitent un zoom élevé** (>1500) pour être visibles

### 2. **Link Decals** (flèches directionnelles)
- Ce sont de **petites flèches blanches** qui indiquent les directions autorisées
- Elles ne changent PAS de couleur selon l'état du feu
- Visibles avec `showLinkDecals="1"`

### 3. **Coloration des lanes**
- En mode 3D uniquement, SUMO peut afficher des "bulles" colorées au-dessus des jonctions
- Non disponible en vue 2D standard

## ✅ Configuration actuelle

Le fichier `gui_settings.xml` est configuré pour afficher les link rules :

```xml
<edges showLinkDecals="1" showLinkRules="1" hideConnectors="0"/>
```

**Résultat attendu :**
- Fond vert
- Routes noires
- Petits rectangles rouge/vert/jaune sur les connexions internes des 71 jonctions TLS
- Noms de rues en blanc

## 🔍 Comment vérifier que les feux fonctionnent

1. **Lancer la simulation** : `python main.py --sumo --sumo-interactive --steps 100`
2. **Zoomer sur une jonction** : Molette de la souris ou bouton zoom
3. **Chercher les rectangles colorés** : Ils apparaissent à l'intérieur des jonctions (zones grises)
4. **Vérifier qu'ils changent de couleur** : Rouge → Vert → Jaune

## 📊 Statistiques du réseau réel d'Abidjan

- **71 feux de circulation** (TLS) détectés automatiquement depuis OpenStreetMap
- **12 193 edges** (routes)
- **Réseau OSM** : Plateau d'Abidjan + ponts (Pont De Gaulle, Pont HKB)
- **Bounding box** : (0,0) → (10653, 10148) mètres

## 🎯 Alternative : Vue 3D

Pour voir des feux plus réalistes :

1. Dans SUMO-GUI, cliquer sur le bouton **3D** (si disponible)
2. Les feux apparaîtront comme des poteaux avec signaux lumineux
3. Nécessite SUMO compilé avec support OpenSceneGraph

## 📝 Conclusion

**Les feux fonctionnent correctement** dans la simulation même s'ils ne sont pas visuellement impressionnants en 2D. Le schéma "real world" est appliqué automatiquement via TraCI au premier pas de simulation.

Si vous ne voyez toujours pas les rectangles colorés, c'est probablement un problème de **zoom insuffisant** — zoomez davantage sur une jonction TLS.
