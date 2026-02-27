"""
Point d'entrée principal du système multi-agent de régulation du trafic
"""
import argparse
import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from environment.traffic_model import TrafficModel
from visualizations.charts import plot_all_visualizations
from loguru import logger


def setup_logging(log_level: str = "INFO"):
    """Configure le système de logging"""
    logger.remove()  # Retirer le handler par défaut
    
    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # File logging
    logger.add(
        "data/logs/simulation_{time}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="7 days",
        compression="zip"
    )


def print_banner():
    """Affiche la bannière du projet"""
    banner = """
    ╔════════════════════════════════════════════════════════════════════╗
    ║                                                                    ║
    ║     🚦 SYSTÈME MULTI-AGENT DE RÉGULATION DU TRAFIC 🚦            ║
    ║                                                                    ║
    ║     Architecture BDI • Communication FIPA-ACL • Framework Mesa    ║
    ║                                                                    ║
    ╚════════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def parse_arguments():
    """Parse les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(
        description="Système Multi-Agent de Régulation du Trafic",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  python main.py                           # Simulation par défaut
  python main.py --steps 1000              # 1000 pas de simulation
  python main.py --scenario rush_hour     # Scénario heure de pointe
  python main.py --config custom.yaml     # Configuration personnalisée
  python main.py --visualize               # Avec visualisation
  python main.py --export results.json    # Exporter les résultats
        """
    )
    
    # Arguments de simulation
    parser.add_argument(
        '--config',
        type=str,
        default='config.yaml',
        help='Fichier de configuration (défaut: config.yaml)'
    )
    
    parser.add_argument(
        '--steps',
        type=int,
        default=None,
        help='Nombre de pas de simulation (défaut: selon config)'
    )
    
    parser.add_argument(
        '--scenario',
        type=str,
        choices=['rush_hour', 'incident', 'normal', 'all'],
        default='normal',
        help='Scénario à exécuter (défaut: normal)'
    )
    
    # Arguments de visualisation
    parser.add_argument(
        '--visualize',
        action='store_true',
        help='Activer la visualisation en temps réel'
    )
    
    parser.add_argument(
        '--animation',
        action='store_true',
        help='Générer une animation de la simulation'
    )
    
    # Arguments d\'export
    parser.add_argument(
        '--export',
        type=str,
        default=None,
        help='Exporter les résultats vers un fichier JSON'
    )
    
    parser.add_argument(
        '--export-csv',
        type=str,
        default=None,
        help='Exporter les données vers un fichier CSV'
    )
    
    # Arguments de logging
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Niveau de logging (défaut: INFO)'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mode verbeux (équivalent à --log-level DEBUG)'
    )
    
    # Arguments de test
    parser.add_argument(
        '--test',
        action='store_true',
        help='Exécuter en mode test (simulation courte)'
    )
    
    parser.add_argument(
        '--seed',
        type=int,
        default=None,
        help='Seed pour la reproductibilité'
    )
    
    # SUMO
    parser.add_argument(
        '--sumo',
        action='store_true',
        help='Lancer avec SUMO-GUI pour visualiser les véhicules en mouvement'
    )
    
    parser.add_argument(
        '--sumo-headless',
        action='store_true',
        help='Lancer SUMO sans interface graphique (mode headless)'
    )
    
    parser.add_argument(
        '--sumo-delay',
        type=int,
        default=0,
        help='Délai d\'affichage SUMO en ms (défaut: 0 = temps réel rapide, 100 = lent mais visible)'
    )
    
    parser.add_argument(
        '--sumo-interactive',
        action='store_true',
        help='Mode interactif: SUMO-GUI attend que vous appuyiez sur Play (▶)'
    )
    
    return parser.parse_args()


def run_simulation(args):
    """Exécute la simulation avec les paramètres donnés"""
    
    # Configuration du logging
    log_level = 'DEBUG' if args.verbose else args.log_level
    setup_logging(log_level)
    
    logger.info("🚀 Initialisation de la simulation...")
    
    # Vérifier que le fichier de config existe
    if not os.path.exists(args.config):
        logger.error(f"❌ Fichier de configuration non trouvé: {args.config}")
        return False
    
    try:
        # Appliquer le seed AVANT la création du modèle pour garantir la reproductibilité
        if args.seed is not None:
            import random
            import numpy as np
            random.seed(args.seed)
            np.random.seed(args.seed)
            logger.info(f"🎲 Seed défini à: {args.seed}")

        # Créer le modèle
        logger.info(f"📋 Chargement de la configuration: {args.config}")
        use_sumo = args.sumo or args.sumo_headless
        sumo_gui = not args.sumo_headless
        sumo_delay = args.sumo_delay
        sumo_auto_start = not args.sumo_interactive
        model = TrafficModel(
            config_path=args.config, use_sumo=use_sumo, sumo_gui=sumo_gui,
            sumo_delay=sumo_delay, sumo_auto_start=sumo_auto_start, scenario=args.scenario
        )
        
        # Déterminer le nombre de pas
        if args.test:
            steps = 100
            logger.info("🧪 Mode test activé (100 pas)")
        elif args.steps:
            steps = args.steps
        else:
            steps = model.max_steps
        
        logger.info(f"⏱️  Durée de simulation: {steps} pas ({steps * model.time_step}s simulés)")
        logger.info(f"📊 Scénario: {args.scenario}")
        
        # Afficher les informations initiales
        logger.info(f"🚗 Véhicules initiaux: {len(model.vehicles)}")
        logger.info(f"🚦 Intersections: {len(model.intersections)}")
        logger.info(f"🗺️  Réseau: {model.road_network.get_statistics()['num_nodes']} nœuds")
        
        # Exécuter la simulation
        logger.info("\n" + "="*70)
        logger.info("🎬 DÉMARRAGE DE LA SIMULATION")
        logger.info("="*70 + "\n")
        
        if args.visualize:
            logger.info("👁️  Mode visualisation activé — graphiques générés en fin de simulation")
        
        # Lancer la simulation
        model.run_simulation(steps=steps)
        
        # Récupérer les statistiques finales
        stats = model.get_statistics()
        
        logger.info("\n" + "="*70)
        logger.info("✅ SIMULATION TERMINÉE")
        logger.info("="*70 + "\n")
        
        # Afficher les résultats
        print_results(stats)
        
        # Export si demandé
        if args.export:
            export_results_json(model, args.export)
        
        if args.export_csv:
            export_results_csv(model, args.export_csv)
        
        # Génération des visualisations si demandé
        if args.visualize:
            logger.info("📊 Génération des visualisations...")
            output_dir = "data/results"
            plot_all_visualizations(model, output_dir=output_dir)
            logger.info(f"✅ Graphiques générés dans {output_dir}/")
        
        # Génération d'animation si demandé
        if args.animation:
            logger.info("🎥 Génération de l'animation...")
            # TODO: Implémenter la génération d'animation
            logger.warning("⚠️  Génération d'animation non encore implémentée")
        
        logger.info("\n🎉 Exécution terminée avec succès!")
        return True
        
    except Exception as e:
        logger.exception(f"❌ Erreur lors de la simulation: {e}")
        return False


def print_results(stats: dict):
    """Affiche les résultats de manière formatée"""
    
    print("\n" + "="*70)
    print("📊 RÉSULTATS DE LA SIMULATION")
    print("="*70)
    
    # Statistiques de simulation
    sim_stats = stats['simulation']
    print(f"\n📈 STATISTIQUES GÉNÉRALES:")
    print(f"  • Temps simulé: {sim_stats['elapsed_time']:.0f} secondes")
    print(f"  • Véhicules créés: {sim_stats['total_vehicles_created']}")
    print(f"  • Véhicules arrivés: {sim_stats['total_vehicles_arrived']}")
    print(f"  • Véhicules actifs (fin): {sim_stats['active_vehicles']}")
    
    # KPIs de performance
    perf_stats = stats['performance']
    print(f"\n🎯 INDICATEURS DE PERFORMANCE (KPIs):")
    print(f"  • Temps de trajet moyen: {perf_stats['average_travel_time']:.2f} secondes")
    print(f"  • Longueur moyenne des files: {perf_stats['average_queue_length']:.2f} véhicules")
    print(f"  • Vitesse moyenne: {perf_stats['average_speed']:.2f} m/s ({perf_stats['average_speed']*3.6:.2f} km/h)")
    print(f"  • Niveau de congestion: {perf_stats['congestion_level']:.2%}")
    
    # Communication
    comm_stats = stats['communication']
    print(f"\n💬 COMMUNICATION:")
    print(f"  • Messages totaux échangés: {comm_stats['total_messages']}")
    print(f"  • Types de messages:")
    for msg_type, count in comm_stats.get('messages_by_type', {}).items():
        print(f"    - {msg_type}: {count}")
    
    # Réseau
    net_stats = stats['network']
    print(f"\n🗺️  RÉSEAU ROUTIER:")
    print(f"  • Nœuds: {net_stats['num_nodes']}")
    print(f"  • Arêtes: {net_stats['num_edges']}")
    print(f"  • Degré moyen: {net_stats['average_degree']:.2f}")
    
    # Gestionnaire de crise
    if 'crisis_manager' in stats:
        cm_stats = stats['crisis_manager']
        print(f"\n🚨 GESTIONNAIRE DE CRISE:")
        print(f"  • Interventions: {cm_stats.get('interventions_count', 0)}")
        print(f"  • Vagues vertes créées: {cm_stats.get('green_waves_created', 0)}")
        print(f"  • Incidents actifs: {cm_stats.get('active_incidents', 0)}")

    # Coordination de voisinage
    if 'coordination' in stats:
        coord = stats['coordination']
        print(f"\n🔗 COORDINATION DE VOISINAGE (ONDES VERTES):")
        print(f"  • Messages de coordination échangés: {coord.get('total_coordination_messages', 0)}")
        print(f"  • Ondes vertes actives (fin sim.): {coord.get('active_green_waves', 0)}")
        print(f"  • Liens de voisinage établis: {coord.get('total_neighbor_links', 0)}")
    
    # Scénarios
    if 'scenarios' in stats:
        sc_stats = stats['scenarios']
        print(f"\n📋 SCÉNARIOS:")
        print(f"  • Heure de pointe - véhicules créés: {sc_stats.get('rush_hour', {}).get('vehicles_created', 0)}")
        incident = sc_stats.get('incident', {})
        print(f"  • Incident '{incident.get('name', 'N/A')}':")
        print(f"    - Véhicules redirigés: {incident.get('vehicles_redirected', 0)}")
        print(f"    - Temps trajet moyen avant incident: {incident.get('avg_travel_time_before_incident', 0):.2f}s")
        print(f"    - Temps trajet moyen pendant incident: {incident.get('avg_travel_time_during_incident', 0):.2f}s")
        print(f"    - Temps trajet moyen après incident: {incident.get('avg_travel_time_after_incident', 0):.2f}s")
    
    print("\n" + "="*70 + "\n")


def export_results_json(model, filepath: str):
    """Exporte les résultats en JSON"""
    import json
    
    logger.info(f"💾 Export des résultats vers {filepath}...")
    
    try:
        stats = model.get_statistics()
        
        # Récupérer les données du datacollector
        df = model.datacollector.get_model_vars_dataframe()
        
        export_data = {
            'statistics': stats,
            'timeseries': df.to_dict('records')
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.success(f"✅ Résultats exportés vers {filepath}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export JSON: {e}")


def export_results_csv(model, filepath: str):
    """Exporte les données en CSV"""
    logger.info(f"💾 Export des données vers {filepath}...")
    
    try:
        df = model.datacollector.get_model_vars_dataframe()
        df.to_csv(filepath, index=True)
        
        logger.success(f"✅ Données exportées vers {filepath}")
        
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'export CSV: {e}")


def main():
    """Fonction principale"""
    # Afficher la bannière
    print_banner()
    
    # Parser les arguments
    args = parse_arguments()
    
    # Exécuter la simulation
    success = run_simulation(args)
    
    # Code de sortie
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
