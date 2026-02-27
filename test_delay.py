"""
Script rapide pour vérifier que le delay SUMO est bien à 0
"""
from sumo_integration.sumo_connector import SumoConnector

# Créer un connecteur avec les paramètres par défaut
connector = SumoConnector()

print("=" * 60)
print("VERIFICATION DU DELAY SUMO")
print("=" * 60)
print(f"Delay configure : {connector.delay} ms")
print()

if connector.delay == 0:
    print("OK - OPTIMISATION ACTIVE : Delay = 0ms (temps reel)")
    print("   La simulation devrait etre 10x plus rapide !")
else:
    print(f"ATTENTION : Delay = {connector.delay}ms")
    print("   La simulation sera lente.")
    print()
    print("Solution : Verifier que sumo_connector.py ligne 45 contient :")
    print("   delay: int = 0")

print("=" * 60)
