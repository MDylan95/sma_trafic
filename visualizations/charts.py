"""
Module de visualisation pour le système de trafic
Génère des graphiques et animations
"""
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.patches import Rectangle, Circle
import seaborn as sns
import numpy as np
import pandas as pd
from typing import List, Tuple


# Configuration du style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 10)
plt.rcParams['font.size'] = 10


class TrafficVisualizer:
    """
    Visualiseur pour la simulation de trafic
    """
    
    def __init__(self, model):
        self.model = model
        self.fig = None
        self.ax = None
    
    def plot_network(self, save_path: str = None):
        """Affiche le réseau routier"""
        fig, ax = plt.subplots(figsize=(10, 10))
        
        # Dessiner les nœuds
        positions = [node.position for node in self.model.road_network.nodes.values()]
        if positions:
            x_coords, y_coords = zip(*positions)
            ax.scatter(x_coords, y_coords, c='lightgray', s=10, alpha=0.5)
        
        # Dessiner les intersections
        for intersection in self.model.intersections:
            x, y = intersection.position
            ax.add_patch(Circle((x, y), radius=50, color='red', alpha=0.7))
            ax.text(x, y, 'I', ha='center', va='center', fontsize=8, color='white')
        
        # Dessiner les véhicules
        for vehicle in self.model.vehicles:
            if vehicle.active:
                x, y = vehicle.position
                ax.add_patch(Circle((x, y), radius=30, color='blue', alpha=0.8))
        
        ax.set_xlim(0, self.model.width)
        ax.set_ylim(0, self.model.height)
        ax.set_xlabel('X (mètres)')
        ax.set_ylabel('Y (mètres)')
        ax.set_title(f'Réseau de Trafic - Step {self.model.current_step}')
        ax.set_aspect('equal')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Réseau sauvegardé: {save_path}")
        
        plt.tight_layout()
        return fig, ax
    
    def plot_kpis(self, datacollector, save_path: str = None):
        """Génère les graphiques des KPIs"""
        df = datacollector.get_model_vars_dataframe()
        
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Indicateurs de Performance (KPIs)', fontsize=16, fontweight='bold')
        
        # 1. Temps de trajet moyen
        axes[0, 0].plot(df.index, df['Average_Travel_Time'], color='#2E86AB', linewidth=2)
        axes[0, 0].set_title('Temps de Trajet Moyen')
        axes[0, 0].set_xlabel('Pas de simulation')
        axes[0, 0].set_ylabel('Temps (secondes)')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Longueur des files
        axes[0, 1].plot(df.index, df['Average_Queue_Length'], color='#A23B72', linewidth=2)
        axes[0, 1].set_title('Longueur Moyenne des Files')
        axes[0, 1].set_xlabel('Pas de simulation')
        axes[0, 1].set_ylabel('Véhicules en attente')
        axes[0, 1].grid(True, alpha=0.3)
        
        # 3. Messages échangés
        axes[0, 2].plot(df.index, df['Total_Messages'], color='#F18F01', linewidth=2)
        axes[0, 2].set_title('Messages Échangés (Cumul)')
        axes[0, 2].set_xlabel('Pas de simulation')
        axes[0, 2].set_ylabel('Nombre de messages')
        axes[0, 2].grid(True, alpha=0.3)
        
        # 4. Véhicules actifs
        axes[1, 0].plot(df.index, df['Active_Vehicles'], color='#6A994E', linewidth=2)
        axes[1, 0].set_title('Véhicules Actifs')
        axes[1, 0].set_xlabel('Pas de simulation')
        axes[1, 0].set_ylabel('Nombre de véhicules')
        axes[1, 0].grid(True, alpha=0.3)
        
        # 5. Vitesse moyenne
        axes[1, 1].plot(df.index, df['Average_Speed'] * 3.6, color='#BC4749', linewidth=2)
        axes[1, 1].set_title('Vitesse Moyenne')
        axes[1, 1].set_xlabel('Pas de simulation')
        axes[1, 1].set_ylabel('Vitesse (km/h)')
        axes[1, 1].grid(True, alpha=0.3)
        
        # 6. Niveau de congestion
        axes[1, 2].plot(df.index, df['Congestion_Level'] * 100, color='#C1121F', linewidth=2)
        axes[1, 2].set_title('Niveau de Congestion')
        axes[1, 2].set_xlabel('Pas de simulation')
        axes[1, 2].set_ylabel('Congestion (%)')
        axes[1, 2].grid(True, alpha=0.3)
        axes[1, 2].axhline(y=50, color='orange', linestyle='--', alpha=0.5, label='Seuil moyen')
        axes[1, 2].legend()
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Graphiques KPIs sauvegardés: {save_path}")
        
        return fig, axes
    
    def plot_heatmap_traffic(self, save_path: str = None):
        """Génère une carte de chaleur du trafic"""
        # Créer une grille
        grid_size = 50
        x_bins = np.linspace(0, self.model.width, grid_size)
        y_bins = np.linspace(0, self.model.height, grid_size)
        
        # Compter les véhicules dans chaque cellule
        traffic_grid = np.zeros((grid_size - 1, grid_size - 1))
        
        for vehicle in self.model.vehicles:
            if vehicle.active:
                x, y = vehicle.position
                x_idx = np.digitize(x, x_bins) - 1
                y_idx = np.digitize(y, y_bins) - 1
                
                if 0 <= x_idx < grid_size - 1 and 0 <= y_idx < grid_size - 1:
                    traffic_grid[y_idx, x_idx] += 1
        
        # Créer la carte de chaleur
        fig, ax = plt.subplots(figsize=(10, 10))
        
        im = ax.imshow(traffic_grid, cmap='YlOrRd', origin='lower', 
                      extent=[0, self.model.width, 0, self.model.height],
                      aspect='auto', interpolation='bilinear')
        
        # Ajouter les intersections
        for intersection in self.model.intersections:
            x, y = intersection.position
            ax.plot(x, y, 'b*', markersize=15, markeredgecolor='white', markeredgewidth=1)
        
        plt.colorbar(im, ax=ax, label='Densité de véhicules')
        ax.set_xlabel('X (mètres)')
        ax.set_ylabel('Y (mètres)')
        ax.set_title('Carte de Chaleur du Trafic')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Carte de chaleur sauvegardée: {save_path}")
        
        return fig, ax
    
    def create_comparison_plot(self, results_dict: dict, save_path: str = None):
        """
        Compare différentes configurations ou algorithmes
        
        Args:
            results_dict: {name: datacollector_dataframe}
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Comparaison des Configurations', fontsize=16, fontweight='bold')
        
        colors = plt.cm.Set2(np.linspace(0, 1, len(results_dict)))
        
        for (name, df), color in zip(results_dict.items(), colors):
            # Temps de trajet
            axes[0, 0].plot(df.index, df['Average_Travel_Time'], 
                          label=name, linewidth=2, color=color)
            
            # Files d'attente
            axes[0, 1].plot(df.index, df['Average_Queue_Length'], 
                          label=name, linewidth=2, color=color)
            
            # Vitesse
            axes[1, 0].plot(df.index, df['Average_Speed'] * 3.6, 
                          label=name, linewidth=2, color=color)
            
            # Congestion
            axes[1, 1].plot(df.index, df['Congestion_Level'] * 100, 
                          label=name, linewidth=2, color=color)
        
        # Configuration des axes
        axes[0, 0].set_title('Temps de Trajet Moyen')
        axes[0, 0].set_ylabel('Temps (s)')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        axes[0, 1].set_title('Longueur Moyenne des Files')
        axes[0, 1].set_ylabel('Véhicules')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)
        
        axes[1, 0].set_title('Vitesse Moyenne')
        axes[1, 0].set_xlabel('Pas de simulation')
        axes[1, 0].set_ylabel('Vitesse (km/h)')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        axes[1, 1].set_title('Niveau de Congestion')
        axes[1, 1].set_xlabel('Pas de simulation')
        axes[1, 1].set_ylabel('Congestion (%)')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Graphique de comparaison sauvegardé: {save_path}")
        
        return fig, axes
    
    def plot_statistics_summary(self, stats: dict, save_path: str = None):
        """Génère un résumé visuel des statistiques"""
        fig, axes = plt.subplots(2, 2, figsize=(12, 8))
        fig.suptitle('Résumé de la Simulation', fontsize=14, fontweight='bold')

        perf = stats['performance']
        sim = stats['simulation']
        comm = stats.get('communication', {})
        cm = stats.get('crisis_manager', {})

        # Panneau texte principal (ligne 0, colonnes 0-1)
        ax_text = axes[0, 0]
        ax_text.axis('off')
        summary_text = (
            f"Véhicules créés : {sim['total_vehicles_created']}\n"
            f"Véhicules arrivés : {sim['total_vehicles_arrived']}\n"
            f"Véhicules actifs : {sim['active_vehicles']}\n\n"
            f"Temps de trajet moyen : {perf['average_travel_time']:.1f} s\n"
            f"Vitesse moyenne : {perf['average_speed']*3.6:.1f} km/h\n"
            f"Congestion : {perf['congestion_level']*100:.1f}%\n"
            f"Files d'attente moy. : {perf['average_queue_length']:.1f} véh."
        )
        ax_text.text(0.05, 0.95, summary_text, ha='left', va='top',
                     fontsize=11, family='monospace',
                     bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3),
                     transform=ax_text.transAxes)

        # Communication
        ax_comm = axes[0, 1]
        ax_comm.axis('off')
        msg_by_type = comm.get('messages_by_type', {})
        if msg_by_type:
            labels = list(msg_by_type.keys())
            values = list(msg_by_type.values())
            ax_comm.pie(values, labels=labels, autopct='%1.0f%%', startangle=90)
            ax_comm.set_title('Messages par type')
        else:
            ax_comm.text(0.5, 0.5, f"Messages totaux :\n{comm.get('total_messages', 0)}",
                         ha='center', va='center', fontsize=12)
            ax_comm.set_title('Communication')

        # Gestionnaire de crise
        ax_cm = axes[1, 0]
        ax_cm.axis('off')
        cm_text = (
            f"Interventions : {cm.get('interventions_count', 0)}\n"
            f"Vagues vertes : {cm.get('green_waves_created', 0)}\n"
            f"Incidents actifs : {cm.get('active_incidents', 0)}"
        )
        ax_cm.text(0.05, 0.95, cm_text, ha='left', va='top',
                   fontsize=11, family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.3),
                   transform=ax_cm.transAxes)
        ax_cm.set_title('Gestionnaire de Crise')

        # Scénarios
        ax_sc = axes[1, 1]
        ax_sc.axis('off')
        scenarios = stats.get('scenarios', {})
        rh = scenarios.get('rush_hour', {})
        inc = scenarios.get('incident', {})
        sc_text = (
            f"Rush hour véhicules : {rh.get('vehicles_created', 0)}\n"
            f"Incident : {inc.get('name', 'N/A')}\n"
            f"  Redirigés : {inc.get('vehicles_redirected', 0)}\n"
            f"  Avant : {inc.get('avg_travel_time_before_incident', 0):.1f} s\n"
            f"  Pendant : {inc.get('avg_travel_time_during_incident', 0):.1f} s"
        )
        ax_sc.text(0.05, 0.95, sc_text, ha='left', va='top',
                   fontsize=11, family='monospace',
                   bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.3),
                   transform=ax_sc.transAxes)
        ax_sc.set_title('Scénarios')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Résumé sauvegardé: {save_path}")

        return fig


def plot_all_visualizations(model, output_dir: str = "data/results"):
    """
    Génère toutes les visualisations
    """
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    visualizer = TrafficVisualizer(model)
    
    print("\n📊 Génération des visualisations...")
    
    # 1. Réseau
    visualizer.plot_network(save_path=f"{output_dir}/network.png")
    
    # 2. KPIs
    visualizer.plot_kpis(model.datacollector, save_path=f"{output_dir}/kpis.png")
    
    # 3. Carte de chaleur
    visualizer.plot_heatmap_traffic(save_path=f"{output_dir}/heatmap.png")
    
    # 4. Résumé
    stats = model.get_statistics()
    visualizer.plot_statistics_summary(stats, save_path=f"{output_dir}/summary.png")
    
    print(f"✅ Toutes les visualisations générées dans {output_dir}/")
    
    plt.close('all')


if __name__ == "__main__":
    print("Module de visualisation - Utilisez plot_all_visualizations(model)")
