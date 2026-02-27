"""
Script de diagnostic pour l'incident du Pont De Gaulle
Vérifie que les edges SUMO existent et teste le blocage
"""
import os
import sys
import time

# Ajouter le chemin SUMO
if 'SUMO_HOME' in os.environ:
    tools = os.path.join(os.environ['SUMO_HOME'], 'tools')
    sys.path.append(tools)
else:
    sys.exit("Veuillez définir la variable d'environnement 'SUMO_HOME'")

import traci
import sumolib

def test_incident_blocking():
    """Test le blocage du Pont De Gaulle"""
    
    # Lancer SUMO
    sumocfg = os.path.join("sumo_integration", "abidjan.sumocfg")
    
    sumo_cmd = [
        "sumo-gui",
        "-c", sumocfg,
        "--quit-on-end", "false",
        "--start", "true",
        "--delay", "100"
    ]
    
    print("🚀 Lancement de SUMO...")
    traci.start(sumo_cmd, port=8813)
    
    print("✅ SUMO connecté\n")
    
    # Récupérer la liste des edges
    all_edges = traci.edge.getIDList()
    print(f"📊 Total edges dans SUMO: {len(all_edges)}\n")
    
    # Construire les IDs des edges du Pont De Gaulle (colonne 2)
    rows = 6
    bridge_col = 2
    bridge_edge_ids = []
    
    for r in range(rows - 1):
        bridge_edge_ids.append(f"e_n{r}_{bridge_col}_to_n{r+1}_{bridge_col}")
        bridge_edge_ids.append(f"e_n{r+1}_{bridge_col}_to_n{r}_{bridge_col}")
    
    print(f"🌉 Edges du Pont De Gaulle attendus ({len(bridge_edge_ids)}):")
    for edge_id in bridge_edge_ids:
        exists = edge_id in all_edges
        status = "✅" if exists else "❌"
        print(f"  {status} {edge_id}")
        
        if exists:
            # Tester le blocage
            try:
                lane_count = traci.edge.getLaneNumber(edge_id)
                print(f"      → {lane_count} lanes")
                
                # Bloquer l'edge
                traci.edge.setDisallowed(edge_id, ["passenger", "bus", "emergency"])
                print(f"      → Bloqué avec setDisallowed()")
                
                # Vérifier
                for lane_idx in range(lane_count):
                    lane_id = f"{edge_id}_{lane_idx}"
                    traci.lane.setMaxSpeed(lane_id, 0.0)
                    speed = traci.lane.getMaxSpeed(lane_id)
                    print(f"      → Lane {lane_idx}: vitesse max = {speed} m/s")
                    
            except Exception as e:
                print(f"      ❌ Erreur: {e}")
    
    print("\n🟥 Test du polygone rouge:")
    try:
        spacing = 500.0
        x_center = bridge_col * spacing
        y_bottom = 0.0
        y_top = (rows - 1) * spacing
        half_w = 60.0
        
        shape = [
            (x_center - half_w, y_bottom),
            (x_center + half_w, y_bottom),
            (x_center + half_w, y_top),
            (x_center - half_w, y_top),
        ]
        
        poly_id = "test_incident_polygon"
        
        traci.polygon.add(
            poly_id,
            shape,
            color=(255, 0, 0, 180),
            fill=True,
            polygonType="incident",
            layer=10
        )
        
        # Forcer la couleur
        traci.polygon.setColor(poly_id, (255, 0, 0, 180))
        
        print(f"  ✅ Polygone créé: {poly_id}")
        print(f"  📍 Position: x={x_center}, y={y_bottom} à {y_top}")
        print(f"  🎨 Couleur: rouge (255, 0, 0, 180)")
        print("\n👀 Vérifiez dans SUMO-GUI si le polygone est ROUGE")
        
    except Exception as e:
        print(f"  ❌ Erreur création polygone: {e}")
    
    print("\n⏸️  Appuyez sur Ctrl+C pour arrêter...")
    
    try:
        while True:
            traci.simulationStep()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n🛑 Arrêt du test")
    
    traci.close()

if __name__ == "__main__":
    test_incident_blocking()
