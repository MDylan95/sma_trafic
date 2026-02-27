"""
Script d'analyse des données stockées dans PostgreSQL
Permet de visualiser et comparer les simulations
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from utils.database import PostgreSQLDatabase
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from tabulate import tabulate


class SimulationAnalyzer:
    """Analyseur de simulations depuis PostgreSQL"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.db = PostgreSQLDatabase(config_path=config_path)
    
    def list_simulations(self):
        """Liste toutes les simulations"""
        simulations = self.db.get_all_simulations()
        
        if not simulations:
            print("Aucune simulation trouvée dans la base de données.")
            return
        
        # Préparer les données pour l'affichage
        data = []
        for sim in simulations:
            data.append([
                sim['simulation_id'],
                sim['simulation_name'],
                sim['scenario'],
                sim.get('num_vehicles', 'N/A'),
                sim.get('algorithm_routing', 'N/A'),
                sim.get('algorithm_traffic_light', 'N/A'),
                sim['status'],
                sim['start_time'].strftime('%Y-%m-%d %H:%M') if sim.get('start_time') else 'N/A'
            ])
        
        headers = ['ID', 'Nom', 'Scénario', 'Véhicules', 'Routage', 'Feux', 'Statut', 'Date']
        print("\n📊 SIMULATIONS ENREGISTRÉES\n")
        print(tabulate(data, headers=headers, tablefmt='grid'))
        print()
    
    def show_simulation_details(self, simulation_id: int):
        """Affiche les détails d'une simulation"""
        sim = self.db.get_simulation(simulation_id)
        
        if not sim:
            print(f"❌ Simulation {simulation_id} non trouvée")
            return
        
        print(f"\n{'='*70}")
        print(f"DÉTAILS DE LA SIMULATION {simulation_id}")
        print(f"{'='*70}\n")
        
        print(f"Nom: {sim['simulation_name']}")
        print(f"Scénario: {sim['scenario']}")
        print(f"Statut: {sim['status']}")
        print(f"Début: {sim['start_time']}")
        print(f"Fin: {sim.get('end_time', 'N/A')}")
        print(f"Durée: {sim.get('duration_seconds', 'N/A')} secondes")
        print(f"Véhicules: {sim.get('num_vehicles', 'N/A')}")
        print(f"Intersections: {sim.get('num_intersections', 'N/A')}")
        print(f"Algorithme routage: {sim.get('algorithm_routing', 'N/A')}")
        print(f"Algorithme feux: {sim.get('algorithm_traffic_light', 'N/A')}")
        
        # Statistiques détaillées
        stats = self.db.get_simulation_statistics(simulation_id)
        
        print(f"\n{'='*70}")
        print("STATISTIQUES")
        print(f"{'='*70}\n")
        
        # Véhicules
        v_stats = stats['vehicles']
        print("📊 Véhicules:")
        print(f"  • Total créés: {v_stats.get('total_vehicles', 0)}")
        print(f"  • Arrivés à destination: {v_stats.get('vehicles_arrived', 0)}")
        print(f"  • Temps de trajet moyen: {v_stats.get('avg_travel_time', 0):.2f} s")
        print(f"  • Distance moyenne: {v_stats.get('avg_distance', 0):.2f} m")
        print(f"  • Vitesse moyenne: {v_stats.get('avg_speed', 0):.2f} m/s ({v_stats.get('avg_speed', 0)*3.6:.2f} km/h)")
        print(f"  • Changements de route moyens: {v_stats.get('avg_route_changes', 0):.2f}")
        
        # Intersections
        i_stats = stats['intersections']
        print(f"\n🚦 Intersections:")
        print(f"  • Total: {i_stats.get('total_intersections', 0)}")
        print(f"  • Temps d'attente moyen: {i_stats.get('avg_waiting_time', 0):.2f} s")
        print(f"  • Changements de phase: {i_stats.get('total_phase_changes', 0)}")
        print(f"  • Messages de coordination: {i_stats.get('total_coordination_msgs', 0)}")
        
        # Messages
        m_stats = stats['messages']
        print(f"\n💬 Communication:")
        print(f"  • Messages totaux: {m_stats.get('total_messages', 0)}")
        print(f"  • Types de performatives: {m_stats.get('unique_performatives', 0)}")
        
        print()
    
    def plot_kpis_evolution(self, simulation_id: int, save_path: str = None):
        """Affiche l'évolution des KPIs"""
        kpis = self.db.get_kpis_timeseries(simulation_id)
        
        if not kpis:
            print(f"❌ Pas de KPIs pour la simulation {simulation_id}")
            return
        
        # Convertir en DataFrame
        df = pd.DataFrame(kpis)
        
        # Créer les graphiques
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle(f'Évolution des KPIs - Simulation {simulation_id}', 
                     fontsize=16, fontweight='bold')
        
        # Temps de trajet
        axes[0, 0].plot(df['step'], df['average_travel_time'], 'b-', linewidth=2)
        axes[0, 0].set_title('Temps de Trajet Moyen')
        axes[0, 0].set_xlabel('Pas de simulation')
        axes[0, 0].set_ylabel('Temps (s)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # Vitesse moyenne
        axes[0, 1].plot(df['step'], df['average_speed'] * 3.6, 'g-', linewidth=2)
        axes[0, 1].set_title('Vitesse Moyenne')
        axes[0, 1].set_xlabel('Pas de simulation')
        axes[0, 1].set_ylabel('Vitesse (km/h)')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Congestion
        axes[1, 0].plot(df['step'], df['congestion_level'] * 100, 'r-', linewidth=2)
        axes[1, 0].set_title('Niveau de Congestion')
        axes[1, 0].set_xlabel('Pas de simulation')
        axes[1, 0].set_ylabel('Congestion (%)')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Files d'attente
        axes[1, 1].plot(df['step'], df['average_queue_length'], 'orange', linewidth=2)
        axes[1, 1].set_title('Longueur Moyenne des Files')
        axes[1, 1].set_xlabel('Pas de simulation')
        axes[1, 1].set_ylabel('Véhicules')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Graphique sauvegardé: {save_path}")
        else:
            plt.show()
    
    def compare_simulations_plot(self, simulation_ids: list, save_path: str = None):
        """Compare plusieurs simulations"""
        if len(simulation_ids) < 2:
            print("❌ Au moins 2 simulations sont nécessaires pour la comparaison")
            return
        
        results = self.db.compare_simulations(simulation_ids)
        
        if not results:
            print("❌ Pas de données pour ces simulations")
            return
        
        # Préparer les données
        df = pd.DataFrame(results)
        
        # Créer le graphique
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))
        fig.suptitle('Comparaison des Simulations', fontsize=16, fontweight='bold')
        
        # Temps de trajet
        axes[0].bar(range(len(df)), df['avg_travel_time'])
        axes[0].set_title('Temps de Trajet Moyen')
        axes[0].set_ylabel('Temps (s)')
        axes[0].set_xticks(range(len(df)))
        axes[0].set_xticklabels([f"Sim {id}" for id in df['simulation_id']], rotation=45)
        axes[0].grid(True, alpha=0.3, axis='y')
        
        # Congestion
        axes[1].bar(range(len(df)), df['avg_congestion'] * 100, color='coral')
        axes[1].set_title('Niveau de Congestion Moyen')
        axes[1].set_ylabel('Congestion (%)')
        axes[1].set_xticks(range(len(df)))
        axes[1].set_xticklabels([f"Sim {id}" for id in df['simulation_id']], rotation=45)
        axes[1].grid(True, alpha=0.3, axis='y')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Comparaison sauvegardée: {save_path}")
        else:
            plt.show()
        
        # Afficher le tableau de comparaison
        print("\n📊 COMPARAISON DES SIMULATIONS\n")
        table_data = []
        for _, row in df.iterrows():
            table_data.append([
                row['simulation_id'],
                row['simulation_name'],
                row['algorithm_routing'],
                row['algorithm_traffic_light'],
                f"{row['avg_travel_time']:.2f}",
                f"{row['avg_congestion']*100:.2f}%"
            ])
        
        headers = ['ID', 'Nom', 'Routage', 'Feux', 'Temps Moy (s)', 'Congestion']
        print(tabulate(table_data, headers=headers, tablefmt='grid'))
        print()
    
    def export_to_csv(self, simulation_id: int, output_dir: str = "data/exports"):
        """Exporte les données d'une simulation en CSV (KPIs, véhicules, intersections)"""
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        exported = []

        # KPIs
        kpis = self.db.get_kpis_timeseries(simulation_id)
        if kpis:
            df_kpis = pd.DataFrame(kpis)
            kpis_file = f"{output_dir}/simulation_{simulation_id}_kpis.csv"
            df_kpis.to_csv(kpis_file, index=False)
            exported.append(f"KPIs ({len(df_kpis)} lignes) → {kpis_file}")

        # Véhicules
        try:
            vehicles = self.db.get_vehicles(simulation_id)
            if vehicles:
                df_v = pd.DataFrame(vehicles)
                v_file = f"{output_dir}/simulation_{simulation_id}_vehicles.csv"
                df_v.to_csv(v_file, index=False)
                exported.append(f"Véhicules ({len(df_v)} lignes) → {v_file}")
        except Exception as e:
            print(f"⚠️  Véhicules non exportés: {e}")

        # Intersections
        try:
            intersections = self.db.get_intersections(simulation_id)
            if intersections:
                df_i = pd.DataFrame(intersections)
                i_file = f"{output_dir}/simulation_{simulation_id}_intersections.csv"
                df_i.to_csv(i_file, index=False)
                exported.append(f"Intersections ({len(df_i)} lignes) → {i_file}")
        except Exception as e:
            print(f"⚠️  Intersections non exportées: {e}")

        if exported:
            print(f"\n✅ Export terminé dans {output_dir}/:")
            for line in exported:
                print(f"   • {line}")
        else:
            print(f"⚠️  Aucune donnée trouvée pour la simulation {simulation_id}")
    
    def close(self):
        """Ferme la connexion"""
        self.db.close()


def main():
    """Menu interactif"""
    analyzer = SimulationAnalyzer()
    
    print("""
    ╔════════════════════════════════════════════════════════════════╗
    ║                                                                ║
    ║     📊 ANALYSE DES SIMULATIONS - POSTGRESQL 📊                ║
    ║                                                                ║
    ╚════════════════════════════════════════════════════════════════╝
    """)
    
    while True:
        print("\n🔍 OPTIONS:")
        print("  1. Lister toutes les simulations")
        print("  2. Détails d'une simulation")
        print("  3. Visualiser l'évolution des KPIs")
        print("  4. Comparer plusieurs simulations")
        print("  5. Exporter en CSV")
        print("  0. Quitter")
        
        try:
            choice = input("\n👉 Votre choix: ").strip()
            
            if choice == "0":
                print("\n👋 Au revoir!")
                break
            
            elif choice == "1":
                analyzer.list_simulations()
            
            elif choice == "2":
                sim_id = int(input("ID de la simulation: "))
                analyzer.show_simulation_details(sim_id)
            
            elif choice == "3":
                sim_id = int(input("ID de la simulation: "))
                save = input("Sauvegarder le graphique? (o/n): ").lower()
                save_path = f"data/results/kpis_sim_{sim_id}.png" if save == 'o' else None
                analyzer.plot_kpis_evolution(sim_id, save_path)
            
            elif choice == "4":
                ids_str = input("IDs des simulations (séparés par des virgules): ")
                ids = [int(x.strip()) for x in ids_str.split(',')]
                save = input("Sauvegarder le graphique? (o/n): ").lower()
                save_path = "data/results/comparison.png" if save == 'o' else None
                analyzer.compare_simulations_plot(ids, save_path)
            
            elif choice == "5":
                sim_id = int(input("ID de la simulation: "))
                analyzer.export_to_csv(sim_id)
            
            else:
                print("❌ Option invalide")
        
        except KeyboardInterrupt:
            print("\n\n👋 Au revoir!")
            break
        except Exception as e:
            print(f"❌ Erreur: {e}")
    
    analyzer.close()


if __name__ == "__main__":
    # Vérifier si tabulate est installé
    try:
        import tabulate
    except ImportError:
        print("⚠️  Le module 'tabulate' n'est pas installé")
        print("   Installation: pip install tabulate")
        sys.exit(1)
    
    main()
