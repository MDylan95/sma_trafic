"""
Vérifier les coordonnées réelles des nœuds dans le réseau SUMO
"""
import xml.etree.ElementTree as ET

# Lire le fichier réseau SUMO
tree = ET.parse('sumo_integration/abidjan.net.xml')
root = tree.getroot()

# Extraire tous les nœuds (sauf les internes qui commencent par ':')
nodes = {}
for node in root.findall('.//node'):
    node_id = node.get('id')
    if not node_id.startswith(':'):
        x = float(node.get('x'))
        y = float(node.get('y'))
        nodes[node_id] = (x, y)

# Grouper par ligne (y constant)
print("=" * 60)
print("COORDONNÉES DES NŒUDS SUMO")
print("=" * 60)

# Extraire les nœuds de la première ligne (y=0)
line0_nodes = [(nid, x, y) for nid, (x, y) in nodes.items() if y == 0.0]
line0_nodes.sort(key=lambda n: n[1])  # Trier par x

print("\nLigne 0 (y=0):")
for nid, x, y in line0_nodes:
    col = int(x / 500) if x > 0 else 0
    print(f"  {nid}: x={x:6.1f}, y={y:6.1f} → Colonne {col}")

# Identifier les colonnes
print("\n" + "=" * 60)
print("IDENTIFICATION DES RUES")
print("=" * 60)

# Selon generate_network.py:
# c=0 → Rue Yopougon
# c=1 → Rue Adjamé
# c=2 → Pont De Gaulle
# c=3 → Pont HKB

x_positions = sorted(set(x for x, y in nodes.values()))
print(f"\nPositions X uniques: {x_positions}")

for i, x in enumerate(x_positions):
    if i == 0:
        rue = "Rue Yopougon"
    elif i == 1:
        rue = "Rue Adjamé"
    elif i == 2:
        rue = "Pont De Gaulle"
    elif i == 3:
        rue = "Pont HKB"
    elif i == 4:
        rue = "Rue Cocody"
    elif i == 5:
        rue = "Rue Bingerville"
    else:
        rue = f"Colonne {i}"
    
    print(f"  x={x:6.1f} → Colonne {i} → {rue}")

print("\n" + "=" * 60)
print("CONCLUSION")
print("=" * 60)
print(f"\nPour bloquer le Pont De Gaulle:")
print(f"  - Utiliser x = {x_positions[2] if len(x_positions) > 2 else 'N/A'}")
print(f"  - bridge_col devrait être = 2")
print(f"  - Calcul: x_center = bridge_col * 500 = 2 * 500 = 1000")
print(f"\nActuellement, le polygone apparaît à x=500 (Rue Adjamé)")
print(f"Cela suggère que bridge_col = 1 lors de l'exécution")
