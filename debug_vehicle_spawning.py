"""
Script de diagnostic approfondi pour identifier pourquoi les véhicules
ne partent pas des bonnes zones (Abobo/Yopougon) dans SUMO.
"""
import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, '.')

print("=" * 80)
print("DIAGNOSTIC APPROFONDI : GÉNÉRATION DE VÉHICULES DANS LES ZONES")
print("=" * 80)

# 1. Vérifier les constantes importées
print("\n1️⃣ VÉRIFICATION DES CONSTANTES IMPORTÉES")
print("-" * 40)

from sumo_integration.real_network_constants import BBOX_YOPOUGON, BBOX_ABOBO, BBOX_PLATEAU

print(f"BBOX_YOPOUGON = {BBOX_YOPOUGON}")
print(f"BBOX_ABOBO    = {BBOX_ABOBO}")
print(f"BBOX_PLATEAU  = {BBOX_PLATEAU}")

# 2. Vérifier les limites du réseau OSM
print("\n2️⃣ LIMITES DU RÉSEAU OSM")
print("-" * 40)

import xml.etree.ElementTree as ET
net_tree = ET.parse('sumo_integration/abidjan_real.net.xml')
net_root = net_tree.getroot()

location = net_root.find('location')
orig_bounds = location.get('origBoundary')
coords = orig_bounds.split(',')
net_minlon = float(coords[0])
net_minlat = float(coords[1])
net_maxlon = float(coords[2])
net_maxlat = float(coords[3])

print(f"Réseau OSM : Lon [{net_minlon:.4f} à {net_maxlon:.4f}], Lat [{net_minlat:.4f} à {net_maxlat:.4f}]")

# 3. Vérifier si les BBox sont dans les limites du réseau
print("\n3️⃣ VÉRIFICATION DES BBOX DANS LES LIMITES DU RÉSEAU")
print("-" * 40)

def check_bbox_in_network(name, bbox, net_minlon, net_minlat, net_maxlon, net_maxlat):
    lon_min, lat_min, lon_max, lat_max = bbox
    
    in_lon = net_minlon <= lon_min <= net_maxlon and net_minlon <= lon_max <= net_maxlon
    in_lat = net_minlat <= lat_min <= net_maxlat and net_minlat <= lat_max <= net_maxlat
    
    status = "✅" if (in_lon and in_lat) else "❌"
    print(f"{status} {name}:")
    print(f"   Lon: [{lon_min:.4f}, {lon_max:.4f}] {'✓' if in_lon else '✗ HORS LIMITES'}")
    print(f"   Lat: [{lat_min:.4f}, {lat_max:.4f}] {'✓' if in_lat else '✗ HORS LIMITES'}")
    
    return in_lon and in_lat

yop_ok = check_bbox_in_network("Yopougon", BBOX_YOPOUGON, net_minlon, net_minlat, net_maxlon, net_maxlat)
abo_ok = check_bbox_in_network("Abobo", BBOX_ABOBO, net_minlon, net_minlat, net_maxlon, net_maxlat)
pla_ok = check_bbox_in_network("Plateau", BBOX_PLATEAU, net_minlon, net_minlat, net_maxlon, net_maxlat)

# 4. Tester la conversion GPS -> SUMO avec sumolib
print("\n4️⃣ TEST DE CONVERSION GPS → COORDONNÉES SUMO")
print("-" * 40)

try:
    import sumolib
    net = sumolib.net.readNet('sumo_integration/abidjan_real.net.xml')
    
    # Tester quelques points dans chaque zone
    test_points = [
        ("Yopougon centre", (BBOX_YOPOUGON[0] + BBOX_YOPOUGON[2]) / 2, (BBOX_YOPOUGON[1] + BBOX_YOPOUGON[3]) / 2),
        ("Abobo centre", (BBOX_ABOBO[0] + BBOX_ABOBO[2]) / 2, (BBOX_ABOBO[1] + BBOX_ABOBO[3]) / 2),
        ("Plateau centre", (BBOX_PLATEAU[0] + BBOX_PLATEAU[2]) / 2, (BBOX_PLATEAU[1] + BBOX_PLATEAU[3]) / 2),
    ]
    
    for name, lon, lat in test_points:
        x, y = net.convertLonLat2XY(lon, lat)
        
        # Trouver l'edge le plus proche
        edges = net.getNeighboringEdges(x, y, r=500)  # Rayon de 500m
        
        if edges:
            closest_edge, dist = min(edges, key=lambda e: e[1])
            print(f"✅ {name}: GPS({lon:.4f}, {lat:.4f}) → SUMO({x:.1f}, {y:.1f})")
            print(f"   Edge le plus proche: {closest_edge.getID()} (distance: {dist:.1f}m)")
        else:
            print(f"❌ {name}: GPS({lon:.4f}, {lat:.4f}) → SUMO({x:.1f}, {y:.1f})")
            print(f"   AUCUN EDGE TROUVÉ dans un rayon de 500m!")
            
except Exception as e:
    print(f"❌ Erreur sumolib: {e}")

# 5. Vérifier le scénario rush_hour
print("\n5️⃣ VÉRIFICATION DU SCÉNARIO RUSH_HOUR")
print("-" * 40)

from scenarios.rush_hour import setup_scenario, USE_REAL_COORDS

print(f"USE_REAL_COORDS = {USE_REAL_COORDS}")

# Mock model
class MockModel:
    def __init__(self):
        self.use_sumo = True
        self.config = {'scenarios': {'rush_hour_morning': {}}}

model = MockModel()
scenario = setup_scenario(model)

print(f"use_real_coords dans scenario_info: {scenario.get('use_real_coords', False)}")
print(f"\nZones d'origine:")
for zone in scenario['origin_zones']:
    print(f"  - {zone['name']}: bbox={zone.get('bbox', 'ABSENT!')}")

print(f"\nZones de destination:")
for zone in scenario['destination_zones']:
    print(f"  - {zone['name']}: bbox={zone.get('bbox', 'ABSENT!')}")

# 6. Vérifier si les véhicules initiaux utilisent les bonnes coordonnées
print("\n6️⃣ VÉRIFICATION DE LA CRÉATION DES VÉHICULES INITIAUX")
print("-" * 40)

# Lire traffic_model.py pour voir comment les véhicules initiaux sont créés
print("Analyse du code de création des véhicules initiaux...")

import ast

with open('environment/traffic_model.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Chercher la méthode _create_initial_vehicles
if '_create_initial_vehicles' in content:
    # Trouver la ligne où les véhicules sont créés
    lines = content.split('\n')
    in_method = False
    for i, line in enumerate(lines):
        if 'def _create_initial_vehicles' in line:
            in_method = True
            print(f"Méthode _create_initial_vehicles trouvée à la ligne {i+1}")
        elif in_method and 'def ' in line and not line.strip().startswith('#'):
            break
        elif in_method and '_create_vehicle' in line:
            print(f"  Ligne {i+1}: {line.strip()}")

# 7. Vérifier le problème principal
print("\n7️⃣ DIAGNOSTIC DU PROBLÈME PRINCIPAL")
print("-" * 40)

# Le problème est probablement que les véhicules initiaux sont créés AVANT le scénario
# et n'utilisent pas les coordonnées GPS

print("""
HYPOTHÈSE DU PROBLÈME :
-----------------------
Les véhicules initiaux (créés dans __init__ de TrafficModel) n'utilisent PAS
les coordonnées GPS des zones. Ils sont créés avec des positions aléatoires
sur la grille, puis SUMO utilise le fallback (paires O/D pré-calculées).

Le scénario rush_hour génère des véhicules SUPPLÉMENTAIRES avec les bonnes
coordonnées GPS, mais les véhicules initiaux restent aux mauvais endroits.

SOLUTION PROPOSÉE :
-------------------
1. Modifier _create_initial_vehicles() pour utiliser les BBox GPS si use_sumo=True
2. OU désactiver la création de véhicules initiaux quand un scénario est actif
3. OU forcer les véhicules initiaux à partir des zones d'origine du scénario
""")

# 8. Vérifier le nombre de véhicules créés par le scénario vs initiaux
print("\n8️⃣ ANALYSE DU FLUX DE CRÉATION")
print("-" * 40)

# Compter les lignes de log du scénario
print("Pour vérifier, lancez la simulation et observez les logs :")
print("  - 'Véhicule #X: Yopougon → Plateau' = véhicule du scénario (GPS)")
print("  - Pas de log = véhicule initial (position aléatoire)")

print("\n" + "=" * 80)
print("FIN DU DIAGNOSTIC")
print("=" * 80)
