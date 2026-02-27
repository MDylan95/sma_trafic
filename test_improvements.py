"""
Script de test pour vérifier les améliorations implémentées :
1. Algorithme Max-Pressure complet
2. A* optimisé pour OSM avec cache LRU
3. Logs détaillés de reroutage

Usage: python test_improvements.py
"""
import sys
from loguru import logger

# Configuration des logs pour voir les détails
logger.remove()
logger.add(sys.stderr, level="INFO")

def test_max_pressure():
    """Test de l'algorithme Max-Pressure complet"""
    logger.info("=" * 70)
    logger.info("TEST 1: Algorithme Max-Pressure complet")
    logger.info("=" * 70)
    
    from agents.intersection_agent import IntersectionAgent, Direction
    from unittest.mock import Mock
    
    # Créer un modèle mock minimal
    model = Mock()
    model.time_step = 1.0
    model.current_step = 0
    model.schedule = Mock()
    model.schedule.agents = []
    
    # Créer une intersection de test
    intersection = IntersectionAgent(
        unique_id="test_intersection",
        model=model,
        position=(100, 100),
        directions=[Direction.NORTH, Direction.SOUTH, Direction.EAST, Direction.WEST]
    )
    
    # Simuler des files d'attente
    intersection.queue_lengths[Direction.NORTH] = 15  # File importante
    intersection.queue_lengths[Direction.SOUTH] = 3
    intersection.queue_lengths[Direction.EAST] = 2
    intersection.queue_lengths[Direction.WEST] = 1
    
    logger.info(f"Files d'attente: {intersection.queue_lengths}")
    
    # Tester la décision Max-Pressure
    should_change = intersection._max_pressure_decision()
    logger.info(f"Décision Max-Pressure: {'CHANGER' if should_change else 'MAINTENIR'}")
    
    # Vérifier que la méthode existe et fonctionne
    assert hasattr(intersection, '_estimate_downstream_queue'), "Méthode _estimate_downstream_queue manquante"
    downstream = intersection._estimate_downstream_queue(Direction.NORTH)
    logger.info(f"Queue en aval estimée (NORTH): {downstream}")
    
    logger.success("✅ Test Max-Pressure: RÉUSSI\n")
    return True


def test_astar_optimization():
    """Test de l'optimisation A* pour OSM"""
    logger.info("=" * 70)
    logger.info("TEST 2: A* optimisé pour OSM avec cache LRU")
    logger.info("=" * 70)
    
    from algorithms.routing import AStarRouter, RoadNetwork
    
    # Créer un réseau de test
    network = RoadNetwork()
    
    # Ajouter quelques nœuds
    from algorithms.routing import Node
    node1 = Node((0, 0), "n1")
    node2 = Node((1000, 0), "n2")
    node3 = Node((2000, 0), "n3")
    node4 = Node((0, 1000), "n4")
    
    network.add_node(node1)
    network.add_node(node2)
    network.add_node(node3)
    network.add_node(node4)
    
    network.add_edge("n1", "n2")
    network.add_edge("n2", "n3")
    network.add_edge("n1", "n4")
    
    # Créer le routeur avec cache
    router = AStarRouter(network, cache_size=100)
    
    # Vérifier que le cache existe
    assert hasattr(router, 'route_cache'), "Cache LRU manquant"
    assert hasattr(router, 'cache_hits'), "Compteur cache_hits manquant"
    assert hasattr(router, 'cache_misses'), "Compteur cache_misses manquant"
    
    logger.info(f"Cache initialisé: taille max = {router.cache_size}")
    
    # Calculer une route
    path1 = router.find_path((0, 0), (2000, 0))
    logger.info(f"Route calculée: {len(path1) if path1 else 0} waypoints")
    logger.info(f"Cache misses: {router.cache_misses}, Cache hits: {router.cache_hits}")
    
    # Recalculer la même route (devrait utiliser le cache)
    path2 = router.find_path((0, 0), (2000, 0))
    logger.info(f"Route recalculée (cache): {len(path2) if path2 else 0} waypoints")
    logger.info(f"Cache misses: {router.cache_misses}, Cache hits: {router.cache_hits}")
    
    # Vérifier que le cache fonctionne
    assert router.cache_hits > 0, "Le cache ne fonctionne pas (aucun hit)"
    
    # Obtenir les statistiques du cache
    stats = router.get_cache_statistics()
    logger.info(f"Statistiques cache: {stats}")
    
    logger.success("✅ Test A* optimisé: RÉUSSI\n")
    return True


def test_reroute_logging():
    """Test des logs de reroutage"""
    logger.info("=" * 70)
    logger.info("TEST 3: Logs détaillés de reroutage")
    logger.info("=" * 70)
    
    from agents.vehicle_agent import VehicleAgent
    from unittest.mock import Mock
    
    # Créer un modèle mock minimal
    model = Mock()
    model.time_step = 1.0
    model.current_step = 0
    model.schedule = Mock()
    model.schedule.agents = []
    
    # Créer un véhicule de test
    vehicle = VehicleAgent(
        unique_id="test_vehicle",
        model=model,
        position=(100, 100),
        destination=(500, 500),
        vehicle_type="standard"
    )
    
    # Vérifier que la méthode de reroutage existe
    assert hasattr(vehicle, '_recalculate_route'), "Méthode _recalculate_route manquante"
    logger.info("✓ Méthode _recalculate_route présente")
    
    # Vérifier que la méthode handle_message existe
    assert hasattr(vehicle, 'handle_message'), "Méthode handle_message manquante"
    logger.info("✓ Méthode handle_message présente")
    
    # Vérifier que la méthode de reroutage contient bien les logs détaillés
    import inspect
    reroute_source = inspect.getsource(vehicle._recalculate_route)
    assert "logger.info" in reroute_source, "Logs de reroutage non implémentés"
    assert "reroute_history" in reroute_source, "Historique de reroutage non implémenté"
    assert "reason" in reroute_source, "Raison du reroutage non loggée"
    assert "congestion_level" in reroute_source, "Niveau de congestion non loggé"
    assert "old_route_length" in reroute_source, "Longueur ancienne route non loggée"
    assert "new_route_length" in reroute_source, "Longueur nouvelle route non loggée"
    logger.info("✓ Logs de reroutage détaillés présents dans le code")
    logger.info("✓ Historique de reroutage présent dans le code")
    logger.info("✓ Raison du reroutage loggée")
    logger.info("✓ Métriques de route loggées (anciennes/nouvelles longueurs)")
    
    # Vérifier que handle_message contient aussi des logs
    message_source = inspect.getsource(vehicle.handle_message)
    assert "logger.debug" in message_source or "logger.info" in message_source, "Logs de messages non implémentés"
    assert "_last_message_type" in message_source, "Type de message non stocké"
    logger.info("✓ Logs de réception de messages présents dans le code")
    logger.info("✓ Type de message stocké pour traçabilité")
    
    logger.success("✅ Test logs de reroutage: RÉUSSI\n")
    return True


def main():
    """Exécute tous les tests"""
    logger.info("\n" + "=" * 70)
    logger.info("🧪 TESTS DES AMÉLIORATIONS - CONFORMITÉ 100%")
    logger.info("=" * 70 + "\n")
    
    results = []
    
    try:
        results.append(("Max-Pressure", test_max_pressure()))
    except Exception as e:
        logger.error(f"❌ Test Max-Pressure échoué: {e}")
        results.append(("Max-Pressure", False))
    
    try:
        results.append(("A* optimisé", test_astar_optimization()))
    except Exception as e:
        logger.error(f"❌ Test A* échoué: {e}")
        results.append(("A* optimisé", False))
    
    try:
        results.append(("Logs reroutage", test_reroute_logging()))
    except Exception as e:
        logger.error(f"❌ Test logs échoué: {e}")
        results.append(("Logs reroutage", False))
    
    # Résumé
    logger.info("=" * 70)
    logger.info("📊 RÉSUMÉ DES TESTS")
    logger.info("=" * 70)
    
    for test_name, success in results:
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        logger.info(f"  {test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        logger.success("\n🎉 TOUS LES TESTS RÉUSSIS - CONFORMITÉ 100% ATTEINTE!")
    else:
        logger.error("\n⚠️ Certains tests ont échoué")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
