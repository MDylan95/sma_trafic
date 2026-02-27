# -*- coding: utf-8 -*-
"""
Diagnostic: Affiche le programme de phases de chaque TLS SUMO
pour comprendre la structure reelle des feux.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

try:
    import traci
    import sumolib
except ImportError:
    print("SUMO non disponible")
    sys.exit(1)

SUMOCFG = os.path.join(os.path.dirname(__file__), "sumo_integration", "abidjan_real.sumocfg")

sumo_cmd = [
    "sumo",
    "-c", SUMOCFG,
    "--no-warnings", "true",
    "--quit-on-end", "true",
    "--start",
    "--step-length", "1.0",
]

print("Connexion a SUMO headless...")
traci.start(sumo_cmd, port=8814)
traci.simulationStep()

tls_ids = traci.trafficlight.getIDList()
print(f"\nNombre total de TLS: {len(tls_ids)}")
print("="*60)

# Afficher les 3 premiers TLS pour diagnostic
for tls_id in tls_ids[:3]:
    print(f"\nTLS: {tls_id}")
    
    # Programme de phases
    logics = traci.trafficlight.getAllProgramLogics(tls_id)
    for logic in logics:
        print(f"  Programme: {logic.programID}, {len(logic.phases)} phases")
        for i, p in enumerate(logic.phases):
            print(f"    Phase {i}: state='{p.state}' duration={p.duration}s")
    
    # Etat actuel
    current = traci.trafficlight.getRedYellowGreenState(tls_id)
    current_phase = traci.trafficlight.getPhase(tls_id)
    print(f"  Etat actuel: '{current}' (phase index={current_phase})")
    
    # Liens controlés
    links = traci.trafficlight.getControlledLinks(tls_id)
    print(f"  Liens controles: {len(links)}")
    for j, link in enumerate(links[:4]):
        if link and link[0]:
            print(f"    Lien {j}: {link[0][0]} -> {link[0][1]}")

print("\n" + "="*60)
print("CONCLUSION:")
print("  - Pour feux corrects : utiliser setPhase(tls_id, 0) ou setPhase(tls_id, 2)")
print("  - Phase 0 = premier groupe vert")
print("  - Phase 2 = second groupe vert (si >= 3 phases)")

traci.close()
print("\nDiagnostic termine.")
