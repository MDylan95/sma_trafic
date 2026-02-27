# 🚦 Comment afficher les feux de circulation dans SUMO-GUI

Le réseau réel d'Abidjan contient **71 feux de circulation** détectés automatiquement.

## ✅ Solution : Activer le schéma "real world"

Dans SUMO-GUI, les feux s'affichent via le schéma de visualisation. Voici comment l'activer :

### Méthode 1 : Menu SUMO-GUI (RECOMMANDÉ)

1. **Lancer la simulation** avec `python main.py --sumo --sumo-interactive`
2. Dans SUMO-GUI, cliquer sur **Edit** → **Edit Visualization**
3. Dans l'onglet **Scheme**, sélectionner **"real world"** dans la liste déroulante
4. Cliquer sur **OK**

Vous devriez maintenant voir :
- **Jonctions TLS (feux)** : carrés/cercles **VERTS** (RGB: 0,255,0)
- **Jonctions priorité** : **JAUNES** (RGB: 200,200,0)
- **Routes** : gris foncé sur fond gris (RGB: 50,50,50)
- **Link decals** : petites flèches/triangles colorés (rouge/vert/jaune) à l'entrée des jonctions

### Méthode 2 : Coloration manuelle des jonctions

Si le schéma "real world" ne s'affiche pas :

1. **Edit** → **Edit Visualization**
2. Onglet **Junctions**
3. Dans **Color**, sélectionner **"by type"**
4. Les feux de circulation (`traffic_light`) apparaîtront en **VERT**

### Méthode 3 : Afficher les link decals (état TLS)

Pour voir l'état des feux (rouge/vert/jaune) en temps réel :

1. **Edit** → **Edit Visualization**
2. Onglet **Streets**
3. Cocher **"show link decals"**
4. Des petits triangles/flèches colorés apparaîtront à l'entrée des jonctions :
   - **Rouge** : feu rouge (stop)
   - **Vert** : feu vert (go)
   - **Jaune** : feu jaune (attention)

## 📊 Vérification

Le réseau d'Abidjan contient :
- **71 feux de circulation** (TLS)
- **12 193 edges** (routes)
- **Bounding box** : (0,0) → (10653, 10148) mètres
- **Centre** : x=5326, y=5074

## 🔧 Dépannage

**Problème** : Les jonctions sont toutes jaunes (pas de vert)
**Solution** : Le schéma par défaut est actif. Suivre la Méthode 1 ci-dessus.

**Problème** : Je ne vois pas le schéma "real world"
**Solution** : Le fichier `gui_settings.xml` n'est pas chargé. Vérifier que `abidjan_real.sumocfg` contient :
```xml
<gui-settings-file value="gui_settings.xml"/>
```

**Problème** : Les feux ne changent pas de couleur
**Solution** : C'est normal si la simulation est en pause. Cliquer sur **Play** (▶) pour démarrer.
