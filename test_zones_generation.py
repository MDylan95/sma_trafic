"""
Script de test pour vérifier que les véhicules sont générés dans les bonnes zones (Abobo, Yopougon).
"""
import sys
sys.path.insert(0, '.')

from scenarios.rush_hour import setup_scenario, get_origin_position, get_destination_position

# Mock model simple
class MockModel:
    def __init__(self):
        self.use_sumo = True
        self.config = {
            'scenarios': {
                'rush_hour_morning': {
                    'name': 'Heure de pointe matinale',
                    'description': 'Flux Yopougon/Abobo vers Plateau',
                    'start_time': 0,
                    'duration': 3600,
                    'vehicle_generation_rate': 2.0
                }
            }
        }

model = MockModel()
scenario_info = setup_scenario(model)

print("=" * 80)
print("TEST DE GÉNÉRATION DES VÉHICULES DANS LES ZONES D'ABIDJAN")
print("=" * 80)
print()

print(f"Scénario: {scenario_info['name']}")
print(f"Utilise coordonnées GPS réelles: {scenario_info.get('use_real_coords', False)}")
print()

print("Zones d'origine configurées:")
for zone in scenario_info['origin_zones']:
    print(f"  - {zone['name']}: {zone.get('bbox', zone.get('coordinates', 'N/A'))}")

print("\nZones de destination configurées:")
for zone in scenario_info['destination_zones']:
    print(f"  - {zone['name']}: {zone.get('bbox', zone.get('coordinates', 'N/A'))}")

print("\n" + "=" * 80)
print("TEST DE 20 GÉNÉRATIONS DE POSITIONS")
print("=" * 80)

from sumo_integration.real_network_constants import (
    BBOX_YOPOUGON, BBOX_ABOBO, BBOX_PLATEAU
)

print(f"\nBBox Yopougon: {BBOX_YOPOUGON}")
print(f"BBox Abobo:    {BBOX_ABOBO}")
print(f"BBox Plateau:  {BBOX_PLATEAU}")

yopougon_count = 0
abobo_count = 0
plateau_count = 0
other_count = 0

print("\nGénération de 20 positions d'origine:")
for i in range(20):
    origin = get_origin_position(scenario_info)
    
    # Déterminer dans quelle zone tombe cette position
    lon, lat = origin
    
    zone_name = "Autre"
    if BBOX_YOPOUGON[0] <= lon <= BBOX_YOPOUGON[2] and BBOX_YOPOUGON[1] <= lat <= BBOX_YOPOUGON[3]:
        zone_name = "Yopougon"
        yopougon_count += 1
    elif BBOX_ABOBO[0] <= lon <= BBOX_ABOBO[2] and BBOX_ABOBO[1] <= lat <= BBOX_ABOBO[3]:
        zone_name = "Abobo"
        abobo_count += 1
    else:
        other_count += 1
    
    print(f"  {i+1}. Origine: ({lon:.4f}, {lat:.4f}) -> Zone: {zone_name}")

print(f"\nRésumé des origines:")
print(f"  - Yopougon: {yopougon_count}/20 ({yopougon_count*5}%)")
print(f"  - Abobo:    {abobo_count}/20 ({abobo_count*5}%)")
print(f"  - Autre:    {other_count}/20 ({other_count*5}%)")

print("\nGénération de 10 positions de destination:")
for i in range(10):
    dest = get_destination_position(scenario_info)
    
    lon, lat = dest
    
    zone_name = "Autre"
    if BBOX_PLATEAU[0] <= lon <= BBOX_PLATEAU[2] and BBOX_PLATEAU[1] <= lat <= BBOX_PLATEAU[3]:
        zone_name = "Plateau"
        plateau_count += 1
    
    print(f"  {i+1}. Destination: ({lon:.4f}, {lat:.4f}) -> Zone: {zone_name}")

print(f"\nRésumé des destinations:")
print(f"  - Plateau: {plateau_count}/10 ({plateau_count*10}%)")

print("\n" + "=" * 80)
if yopougon_count > 0 and abobo_count > 0 and plateau_count > 0:
    print("✅ SUCCÈS: Les véhicules sont générés dans les bonnes zones!")
else:
    print("❌ ÉCHEC: Certaines zones ne génèrent pas de véhicules.")
    if yopougon_count == 0:
        print("   - Aucun véhicule généré à Yopougon")
    if abobo_count == 0:
        print("   - Aucun véhicule généré à Abobo")
    if plateau_count == 0:
        print("   - Aucun véhicule généré au Plateau")
print("=" * 80)
