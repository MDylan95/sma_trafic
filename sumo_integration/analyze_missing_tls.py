#!/usr/bin/env python3
"""
Analyse du réseau OSM d'Abidjan pour identifier les intersections
stratégiques qui devraient avoir des feux de circulation (TLS).

Critères d'identification :
1. Jonctions avec degré élevé (4+ connexions)
2. Jonctions sur routes principales (primary, secondary, tertiary)
3. Jonctions prioritaires (priority) sans TLS
4. Jonctions avec fort trafic potentiel (croisement de routes importantes)
"""

import sumolib
import sys
from collections import defaultdict
from typing import List, Tuple, Dict

def analyze_network(net_file: str) -> Dict:
    """
    Analyse le réseau SUMO pour identifier les jonctions candidates pour TLS.
    
    Returns:
        Dict avec statistiques et liste des jonctions candidates
    """
    print(f"[*] Chargement du reseau : {net_file}")
    net = sumolib.net.readNet(net_file)
    
    # Récupérer toutes les jonctions
    all_junctions = list(net.getNodes())
    
    # Séparer les jonctions par type
    tls_junctions = [j for j in all_junctions if j.getType() == "traffic_light"]
    priority_junctions = [j for j in all_junctions if j.getType() == "priority"]
    other_junctions = [j for j in all_junctions if j.getType() not in ["traffic_light", "priority"]]
    
    print(f"\n[STATS] STATISTIQUES DU RESEAU")
    print(f"{'='*60}")
    print(f"Total jonctions       : {len(all_junctions)}")
    print(f"  - TLS (feux)        : {len(tls_junctions)}")
    print(f"  - Priority          : {len(priority_junctions)}")
    print(f"  - Autres            : {len(other_junctions)}")
    print(f"{'='*60}\n")
    
    # Analyser les jonctions prioritaires pour identifier les candidates
    candidates = []
    
    for junction in priority_junctions:
        # Calculer le degré (nombre de connexions)
        incoming = junction.getIncoming()
        outgoing = junction.getOutgoing()
        degree = len(incoming) + len(outgoing)
        
        # Ignorer les jonctions simples (< 4 connexions)
        if degree < 4:
            continue
        
        # Analyser les types de routes connectées
        road_types = set()
        road_names = set()
        max_speed = 0
        
        for edge in incoming + outgoing:
            # Type de route (primary, secondary, tertiary, etc.)
            edge_type = edge.getType() if hasattr(edge, 'getType') else "unknown"
            road_types.add(edge_type)
            
            # Nom de la route
            name = edge.getName() if edge.getName() else "unnamed"
            if name != "unnamed":
                road_names.add(name)
            
            # Vitesse max
            speed = edge.getSpeed()
            if speed > max_speed:
                max_speed = speed
        
        # Calculer un score de priorité
        score = 0
        
        # Score basé sur le degré (plus de connexions = plus important)
        score += degree * 10
        
        # Bonus si routes principales (primary, secondary)
        if any(rt in str(road_types) for rt in ['primary', 'secondary', 'trunk']):
            score += 50
        
        # Bonus si vitesse élevée (routes importantes)
        if max_speed > 13.89:  # > 50 km/h
            score += 30
        
        # Bonus si plusieurs routes nommées se croisent
        if len(road_names) >= 2:
            score += 20
        
        # Stocker la candidate
        candidates.append({
            'id': junction.getID(),
            'coord': junction.getCoord(),
            'degree': degree,
            'road_types': road_types,
            'road_names': road_names,
            'max_speed_kmh': round(max_speed * 3.6, 1),
            'score': score
        })
    
    # Trier par score décroissant
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'total_junctions': len(all_junctions),
        'existing_tls': len(tls_junctions),
        'priority_junctions': len(priority_junctions),
        'candidates': candidates
    }

def print_top_candidates(results: Dict, top_n: int = 30):
    """Affiche les N meilleures candidates pour TLS."""
    candidates = results['candidates'][:top_n]
    
    print(f"\n[TOP] TOP {top_n} JONCTIONS CANDIDATES POUR TLS")
    print(f"{'='*100}")
    print(f"{'Rang':<6} {'ID Jonction':<25} {'Degré':<8} {'Vitesse':<10} {'Score':<8} {'Routes'}")
    print(f"{'-'*100}")
    
    for i, candidate in enumerate(candidates, 1):
        junction_id = candidate['id']
        degree = candidate['degree']
        speed = f"{candidate['max_speed_kmh']} km/h"
        score = candidate['score']
        roads = ', '.join(list(candidate['road_names'])[:2]) if candidate['road_names'] else "unnamed"
        
        print(f"{i:<6} {junction_id:<25} {degree:<8} {speed:<10} {score:<8} {roads[:40]}")
    
    print(f"{'='*100}\n")

def generate_tls_file(results: Dict, output_file: str, output_nod_file: str, top_n: int = 30):
    """
    Génère un fichier .nod.xml pour convertir des jonctions en TLS.
    SUMO générera automatiquement les programmes TLS adaptés.
    """
    candidates = results['candidates'][:top_n]
    
    # Générer le fichier .nod.xml pour netconvert
    with open(output_nod_file, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!-- Jonctions à convertir en feux de circulation (TLS) -->\n')
        f.write('<!-- Générés automatiquement par analyse des jonctions stratégiques -->\n\n')
        f.write('<nodes>\n')
        
        for candidate in candidates:
            junction_id = candidate['id']
            f.write(f'    <!-- Degré: {candidate["degree"]} | Score: {candidate["score"]} -->\n')
            f.write(f'    <node id="{junction_id}" type="traffic_light"/>\n')
        
        f.write('</nodes>\n')
    
    print(f"[OK] Fichier nodes genere : {output_nod_file}")
    print(f"   {len(candidates)} jonctions marquees pour conversion en TLS")
    print(f"   Relancer netconvert pour regenerer le reseau avec les nouveaux TLS\n")

def main():
    net_file = "d:/traffic_sma_project/sumo_integration/abidjan_real.net.xml"
    output_file = "d:/traffic_sma_project/sumo_integration/additional_tls.add.xml"
    
    # Analyser le réseau
    results = analyze_network(net_file)
    
    # Afficher les statistiques
    print(f"\n[RESUME] RESUME DE L'ANALYSE")
    print(f"{'='*60}")
    print(f"Feux existants (OSM)           : {results['existing_tls']}")
    print(f"Jonctions prioritaires         : {results['priority_junctions']}")
    print(f"Candidates identifiees         : {len(results['candidates'])}")
    print(f"{'='*60}\n")
    
    # Afficher les top candidates
    print_top_candidates(results, top_n=30)
    
    # Générer le fichier TLS
    print(f"\n[GEN] GENERATION DU FICHIER TLS")
    print(f"{'='*60}")
    generate_tls_file(results, output_file, top_n=30)
    
    # Recommandations
    print(f"\n[INFO] RECOMMANDATIONS")
    print(f"{'='*60}")
    print(f"1. Vérifier le fichier généré : {output_file}")
    print(f"2. Ajouter ce fichier dans abidjan_real.sumocfg :")
    print(f"   <additional-files value=\"vtypes.add.xml,additional_tls.add.xml\"/>")
    print(f"3. Relancer la simulation pour tester les nouveaux feux")
    print(f"4. Total feux après ajout : {results['existing_tls']} + 30 = {results['existing_tls'] + 30}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
