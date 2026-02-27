"""
Scénario 1 : Heure de pointe matinale
Flux massif allant de Yopougon/Abobo vers le Plateau (Abidjan)
"""
import random
from typing import Dict, List, Tuple

# Importer les vraies coordonnées GPS d'Abidjan
try:
    from sumo_integration.real_network_constants import BBOX_YOPOUGON, BBOX_ABOBO, BBOX_PLATEAU
    USE_REAL_COORDS = True
except ImportError:
    USE_REAL_COORDS = False
    BBOX_YOPOUGON = None
    BBOX_ABOBO = None
    BBOX_PLATEAU = None


def setup_scenario(model, config: Dict = None) -> Dict:
    """
    Configure le scénario d'heure de pointe matinale.
    
    Paramètres:
        model: Instance de TrafficModel
        config: Configuration du scénario (optionnel, utilise config.yaml par défaut)
    
    Returns:
        Dictionnaire avec les informations du scénario
    """
    if config is None:
        config = model.config.get('scenarios', {}).get('rush_hour_morning', {})
    
    # Utiliser les vraies coordonnées GPS si disponibles (réseau OSM)
    if USE_REAL_COORDS and model.use_sumo:
        origin_zones = [
            {'name': 'Yopougon', 'weight': 0.5, 'bbox': BBOX_YOPOUGON},
            {'name': 'Abobo', 'weight': 0.5, 'bbox': BBOX_ABOBO}
        ]
        destination_zones = [
            {'name': 'Plateau', 'weight': 1.0, 'bbox': BBOX_PLATEAU}
        ]
    else:
        # Fallback : coordonnées de grille fictive (pour compatibilité)
        origin_zones = config.get('origin_zones', [
            {'name': 'Yopougon', 'weight': 0.5, 'coordinates': [0, 2500]},
            {'name': 'Abobo', 'weight': 0.5, 'coordinates': [2500, 5000]}
        ])
        destination_zones = config.get('destination_zones', [
            {'name': 'Plateau', 'weight': 1.0, 'coordinates': [2500, 0]}
        ])
    
    scenario_info = {
        'name': config.get('name', 'Heure de pointe matinale'),
        'description': config.get('description', 'Flux Yopougon/Abobo vers Plateau'),
        'start_time': config.get('start_time', 0),
        'duration': config.get('duration', 3600),
        'vehicle_generation_rate': config.get('vehicle_generation_rate', 0.5),
        'origin_zones': origin_zones,
        'destination_zones': destination_zones,
        'vehicles_created': 0,
        'use_real_coords': USE_REAL_COORDS and model.use_sumo
    }
    
    return scenario_info


def should_generate_vehicle(scenario_info: Dict, current_step: int, time_step: float) -> bool:
    """
    Détermine si un véhicule doit être généré à ce pas de temps.
    
    Le taux de génération suit une courbe réaliste d'heure de pointe :
    - Montée progressive (0-30 min)
    - Pic (30-60 min)
    - Descente (60-90 min)
    """
    start = scenario_info['start_time']
    duration = scenario_info['duration']
    base_rate = scenario_info['vehicle_generation_rate']
    
    elapsed = current_step * time_step - start
    
    if elapsed < 0 or elapsed > duration:
        return False
    
    # Courbe en cloche pour simuler le pic de trafic
    progress = elapsed / duration
    if progress < 0.33:
        # Phase de montée
        rate_multiplier = progress / 0.33
    elif progress < 0.66:
        # Phase de pic
        rate_multiplier = 1.0
    else:
        # Phase de descente
        rate_multiplier = (1.0 - progress) / 0.34
    
    adjusted_rate = base_rate * rate_multiplier * time_step
    return random.random() < adjusted_rate


def get_origin_position(scenario_info: Dict) -> Tuple[float, float]:
    """
    Sélectionne une position d'origine pondérée parmi les zones d'origine.
    Simule les départs depuis Yopougon et Abobo.
    
    Returns:
        (lon, lat) si use_real_coords=True, sinon (x, y) en mètres
    """
    origins = scenario_info['origin_zones']
    weights = [z['weight'] for z in origins]
    
    selected_zone = random.choices(origins, weights=weights)[0]
    
    # Si on utilise les vraies coordonnées GPS (réseau OSM)
    if scenario_info.get('use_real_coords', False) and 'bbox' in selected_zone:
        bbox = selected_zone['bbox']  # (lon_min, lat_min, lon_max, lat_max)
        lon = random.uniform(bbox[0], bbox[2])
        lat = random.uniform(bbox[1], bbox[3])
        return (lon, lat)
    
    # Sinon, utiliser les coordonnées de grille fictive
    base_coords = selected_zone.get('coordinates', [0, 0])
    x = base_coords[0] + random.randint(-300, 300)
    y = base_coords[1] + random.randint(-300, 300)
    x = max(0, min(x, 4999))
    y = max(0, min(y, 4999))
    
    return (x, y)


def get_destination_position(scenario_info: Dict) -> Tuple[float, float]:
    """
    Sélectionne une position de destination pondérée.
    Simule les arrivées vers le Plateau.
    
    Returns:
        (lon, lat) si use_real_coords=True, sinon (x, y) en mètres
    """
    destinations = scenario_info['destination_zones']
    weights = [z['weight'] for z in destinations]
    
    selected_zone = random.choices(destinations, weights=weights)[0]
    
    # Si on utilise les vraies coordonnées GPS (réseau OSM)
    if scenario_info.get('use_real_coords', False) and 'bbox' in selected_zone:
        bbox = selected_zone['bbox']  # (lon_min, lat_min, lon_max, lat_max)
        lon = random.uniform(bbox[0], bbox[2])
        lat = random.uniform(bbox[1], bbox[3])
        return (lon, lat)
    
    # Sinon, utiliser les coordonnées de grille fictive
    base_coords = selected_zone.get('coordinates', [0, 0])
    x = base_coords[0] + random.randint(-200, 200)
    y = base_coords[1] + random.randint(-200, 200)
    x = max(0, min(x, 4999))
    y = max(0, min(y, 4999))
    
    return (x, y)


def _get_vehicle_type_for_rush_hour() -> Tuple[str, float]:
    """
    Retourne un type de véhicule et sa vitesse max selon la distribution rush hour.
    Distribution : 80% standard, 15% bus_sotra, 5% autres urgences
    """
    r = random.random()
    if r < 0.80:
        return "standard", 13.89
    elif r < 0.95:
        return "bus_sotra", 11.11
    elif r < 0.97:
        return "ambulance", 22.22
    elif r < 0.99:
        return "pompier", 19.44
    else:
        return "police", 22.22


def run_scenario_step(model, scenario_info: Dict) -> bool:
    """
    Exécute un pas du scénario d'heure de pointe.
    Génère des véhicules selon le profil de trafic.
    
    Returns:
        True si un véhicule a été créé
    """
    if not should_generate_vehicle(scenario_info, model.current_step, model.time_step):
        return False
    
    origin = get_origin_position(scenario_info)
    destination = get_destination_position(scenario_info)
    
    vehicle_id = f"rush_hour_vehicle_{scenario_info['vehicles_created']}"
    vehicle_type, max_speed = _get_vehicle_type_for_rush_hour()
    
    # Log pour vérifier le flux géographique (tous les 10 véhicules)
    if scenario_info['vehicles_created'] % 10 == 0 and scenario_info.get('use_real_coords', False):
        from loguru import logger
        # Déterminer la zone d'origine
        origin_zone = "?"
        for zone in scenario_info['origin_zones']:
            if 'bbox' in zone:
                bbox = zone['bbox']
                if bbox[0] <= origin[0] <= bbox[2] and bbox[1] <= origin[1] <= bbox[3]:
                    origin_zone = zone['name']
                    break
        logger.info(f"🚗 Véhicule #{scenario_info['vehicles_created']}: {origin_zone} → Plateau (GPS: {origin[0]:.4f}, {origin[1]:.4f})")
    
    # Créer le véhicule avec les positions de zone du scénario
    # Si use_real_coords=True, origin et destination sont des coordonnées GPS (lon, lat)
    vehicle = model._create_vehicle(
        vehicle_id,
        vehicle_type=vehicle_type,
        start_pos=origin,
        dest_pos=destination,
        use_gps_coords=scenario_info.get('use_real_coords', False)
    )
    
    if vehicle is not None:
        scenario_info['vehicles_created'] += 1
        return True
    
    return False


def get_scenario_statistics(scenario_info: Dict) -> Dict:
    """Retourne les statistiques du scénario"""
    return {
        'name': scenario_info['name'],
        'vehicles_created': scenario_info['vehicles_created'],
        'generation_rate': scenario_info['vehicle_generation_rate'],
        'origin_zones': [z['name'] for z in scenario_info['origin_zones']],
        'destination_zones': [z['name'] for z in scenario_info['destination_zones']]
    }
