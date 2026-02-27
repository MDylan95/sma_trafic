# 🚦 Comment afficher les feux de circulation dans SUMO-GUI

Le réseau réel d'Abidjan contient **71 feux de circulation** détectés automatiquement depuis OpenStreetMap.

## ✅ Configuration automatique (déjà appliquée)

Le fichier `gui_settings.xml` a été optimisé avec :
- **Zoom initial élevé** (2000) pour voir les détails dès le démarrage
- **Exagération des jonctions** (2.0) pour agrandir les intersections
- **Affichage des indices TLS** activé par défaut
- **Affichage des phases** activé

Les feux **devraient être visibles automatiquement** au démarrage de SUMO-GUI.

## 🔧 Si les feux ne sont toujours pas visibles

### Méthode 1 : Menu Edit (le plus fiable)

Une fois SUMO-GUI lancé :

1. **Menu** → **Edit** → **Edit Visualization**
2. Onglet **"Streets"** :
   - ✅ Cocher **"show link decals"**
   - ✅ Cocher **"show link rules"**
3. Onglet **"Junctions"** :
   - ✅ Cocher **"show TLS index"**
   - ✅ Cocher **"show TLS phase index"**
   - Augmenter **"size exaggeration"** à **2.0**
4. Cliquer **OK**

### Méthode 2 : Raccourci clavier

Appuyez sur **`Ctrl+T`** pour basculer l'affichage des TLS (Traffic Light Systems).

### Méthode 3 : Zoom manuel

Les feux ne sont visibles qu'avec un **zoom suffisant** (> 1000).
- Utilisez la **molette de la souris** pour zoomer
- Ou **clic droit** → **Recenter View** pour centrer sur le réseau

## 📍 Apparence des feux

Les feux apparaissent comme des **petits carrés colorés** aux intersections :
- 🟥 **Rouge** : arrêt obligatoire
- 🟨 **Jaune** : ralentir
- 🟩 **Vert** : passage autorisé

Les couleurs changent dynamiquement selon les phases du feu.

## ✅ Vérification

Pour confirmer que les feux fonctionnent :
1. Zoomer sur une intersection (zoom > 1000)
2. Observer les **petits carrés colorés** qui changent de couleur
3. Vérifier que les véhicules s'arrêtent au feu rouge

**Note** : Les 71 feux sont gérés automatiquement par Mesa et synchronisés avec SUMO via TraCI.
