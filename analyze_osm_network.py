"""
Script d'analyse pour vérifier si le réseau OSM correspond vraiment à Abidjan, Côte d'Ivoire
"""
import xml.etree.ElementTree as ET
import math

print("=" * 80)
print("ANALYSE DU RÉSEAU OSM : CORRESPONDANCE AVEC ABIDJAN, CÔTE D'IVOIRE")
print("=" * 80)

# 1. Analyser les limites géographiques depuis le fichier .net.xml
net_tree = ET.parse('sumo_integration/abidjan_real.net.xml')
net_root = net_tree.getroot()

location = net_root.find('location')
if location is not None:
    orig_bounds = location.get('origBoundary')
    if orig_bounds:
        coords = orig_bounds.split(',')
        minlon = float(coords[0])
        minlat = float(coords[1])
        maxlon = float(coords[2])
        maxlat = float(coords[3])
    else:
        print("❌ Impossible de trouver les limites géographiques")
        exit(1)
else:
    print("❌ Pas de balise 'location' dans le fichier réseau")
    exit(1)

if True:
    
    print(f'\n1️⃣ LIMITES GÉOGRAPHIQUES DU RÉSEAU OSM :')
    print(f'   Latitude  : {minlat:.6f} à {maxlat:.6f}')
    print(f'   Longitude : {minlon:.6f} à {maxlon:.6f}')
    
    center_lat = (minlat + maxlat) / 2
    center_lon = (minlon + maxlon) / 2
    print(f'\n   Centre géographique : Lat {center_lat:.6f}, Lon {center_lon:.6f}')
    
    # Coordonnées réelles d'Abidjan
    ABIDJAN_CENTER = (5.316667, -4.033333)  # Plateau, centre d'Abidjan
    
    # Distance haversine
    dlat = abs(center_lat - ABIDJAN_CENTER[0])
    dlon = abs(center_lon - ABIDJAN_CENTER[1])
    dist_km = math.sqrt(dlat**2 + dlon**2) * 111  # 1° ≈ 111 km
    
    print(f'\n2️⃣ COMPARAISON AVEC ABIDJAN RÉEL :')
    print(f'   Centre d\'Abidjan (Plateau) : Lat {ABIDJAN_CENTER[0]:.6f}, Lon {ABIDJAN_CENTER[1]:.6f}')
    print(f'   Distance du centre OSM au centre Abidjan : {dist_km:.2f} km')
    
    if dist_km < 5:
        print(f'   ✅ Le réseau OSM EST CENTRÉ SUR ABIDJAN!')
    elif dist_km < 20:
        print(f'   ⚠️  Le réseau semble proche d\'Abidjan (à {dist_km:.0f} km)')
    else:
        print(f'   ❌ Le réseau NE correspond PAS à Abidjan (trop éloigné : {dist_km:.0f} km)')

# 2. Rechercher les noms de rues dans le fichier réseau SUMO
print(f'\n3️⃣ RECHERCHE DE RUES ET INFRASTRUCTURES D\'ABIDJAN :')

streets_with_names = []
abidjan_landmarks = []

# Mots-clés caractéristiques d'Abidjan
ABIDJAN_KEYWORDS = [
    'Abidjan', 'Plateau', 'Cocody', 'Yopougon', 'Abobo', 'Adjamé', 'Treichville',
    'Marcory', 'Koumassi', 'Port-Bouët', 'Attécoubé',
    'Gaulle', 'Houphouët', 'Boigny', 'HKB', 'Félix', 'FHB',
    'Boulevard', 'Avenue', 'Rue', 'Latrille', 'Carde', 'Franchet',
    'Pont', 'Charles de Gaulle', 'Ébrié', 'Ekra', 'Hassan'
]

# Lire les noms depuis les edges du réseau SUMO
for edge in net_root.findall('edge'):
    # Chercher le paramètre name dans les edges
    name_param = edge.find("param[@key='name']")
    if name_param is not None:
        name = name_param.get('value')
        if name and name not in streets_with_names:
            streets_with_names.append(name)
            # Vérifier si c'est un landmark d'Abidjan
            for keyword in ABIDJAN_KEYWORDS:
                if keyword.lower() in name.lower():
                    abidjan_landmarks.append(name)
                    break

print(f'\n   Nombre total de rues nommées : {len(streets_with_names)}')
print(f'   Rues avec noms caractéristiques d\'Abidjan : {len(abidjan_landmarks)}')

if abidjan_landmarks:
    print(f'\n   🎯 LANDMARKS D\'ABIDJAN TROUVÉS :')
    for i, name in enumerate(abidjan_landmarks[:15], 1):
        print(f'      {i}. {name}')
    if len(abidjan_landmarks) > 15:
        print(f'      ... et {len(abidjan_landmarks) - 15} autres')

# 3. Vérifier la présence des ponts
print(f'\n4️⃣ VÉRIFICATION DES INFRASTRUCTURES CRITIQUES :')

from sumo_integration.real_network_constants import PONT_DE_GAULLE_EDGES, PONT_HKB_EDGES

# Le fichier net.xml a déjà été lu au début du script
all_edges = [edge.get('id') for edge in net_root.findall('edge')]

pont_gaulle_found = any(edge in all_edges for edge in PONT_DE_GAULLE_EDGES)
pont_hkb_found = any(edge in all_edges for edge in PONT_HKB_EDGES)

print(f'   Pont De Gaulle (edges {PONT_DE_GAULLE_EDGES}) : {"✅ TROUVÉ" if pont_gaulle_found else "❌ ABSENT"}')
print(f'   Pont HKB (échantillon d\'edges) : {"✅ TROUVÉ" if pont_hkb_found else "❌ ABSENT"}')

# 4. Statistiques du réseau
num_nodes = len([n for n in net_root.findall('junction') if n.get('type') != 'internal'])
num_edges = len([e for e in net_root.findall('edge') if not e.get('id').startswith(':')])

print(f'\n5️⃣ STATISTIQUES DU RÉSEAU :')
print(f'   Nœuds (junctions) : {num_nodes}')
print(f'   Arêtes (edges)    : {num_edges}')
print(f'   Rues nommées      : {len(streets_with_names)}')

# Surface approximative
surface_km2 = abs(maxlon - minlon) * abs(maxlat - minlat) * 111 * 111
print(f'   Surface couverte  : ~{surface_km2:.1f} km²')

# 5. Exemples de noms de rues
print(f'\n6️⃣ EXEMPLES DE NOMS DE RUES (20 premiers) :')
for i, name in enumerate(streets_with_names[:20], 1):
    print(f'   {i}. {name}')

# CONCLUSION
print(f'\n' + '=' * 80)
print('📊 CONCLUSION DE L\'ANALYSE')
print('=' * 80)

score = 0
details = []

if dist_km < 5:
    score += 3
    details.append("✅ Centré sur Abidjan (distance < 5 km)")
elif dist_km < 20:
    score += 2
    details.append("⚠️  Proche d'Abidjan mais légèrement décalé")
else:
    score += 0
    details.append("❌ Trop éloigné d'Abidjan")

if len(abidjan_landmarks) > 10:
    score += 2
    details.append(f"✅ Nombreux landmarks d'Abidjan trouvés ({len(abidjan_landmarks)})")
elif len(abidjan_landmarks) > 0:
    score += 1
    details.append(f"⚠️  Quelques landmarks trouvés ({len(abidjan_landmarks)})")
else:
    score += 0
    details.append("❌ Aucun landmark caractéristique d'Abidjan")

if pont_gaulle_found or pont_hkb_found:
    score += 2
    details.append("✅ Infrastructures critiques présentes (ponts)")
else:
    score += 0
    details.append("❌ Infrastructures critiques absentes")

print()
for detail in details:
    print(f"   {detail}")

print(f'\n   Score de correspondance : {score}/7')

if score >= 6:
    print(f'\n   🎉 VERDICT : Le réseau OSM correspond PARFAITEMENT à Abidjan, Côte d\'Ivoire!')
elif score >= 4:
    print(f'\n   ✅ VERDICT : Le réseau OSM correspond BIEN à Abidjan (quelques imprécisions mineures)')
elif score >= 2:
    print(f'\n   ⚠️  VERDICT : Le réseau semble être PARTIELLEMENT lié à Abidjan')
else:
    print(f'\n   ❌ VERDICT : Le réseau NE correspond PAS à Abidjan!')

print('=' * 80)
