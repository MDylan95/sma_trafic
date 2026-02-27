"""
Nommage des routes du réseau SUMO d'Abidjan.
Associe les IDs d'arêtes à des noms descriptifs pour faciliter l'identification.
"""

def get_road_name(edge_id: str) -> str:
    """
    Retourne le nom descriptif d'une arête basé sur sa position dans le réseau.
    
    Convention de grille 6×6:
    - Colonnes 0-5 (ouest à est)
    - Rangées 0-5 (nord à sud)
    
    Routes principales:
    - Colonne 2-3 (N-S) = Pont De Gaulle (vertical central)
    - Colonne 1-2 (N-S) = Pont HKB (vertical central-ouest)
    - Rangée 2-3 (E-O) = Avenue Principale (horizontal central)
    - Bords = Routes d'accès (entrée/sortie)
    """
    import re
    
    # Routes d'entrée/sortie
    if 'src_south' in edge_id:
        match = re.search(r'src_south_(\d+)', edge_id)
        if match:
            col = int(match.group(1))
            direction = "vers" if "to_n" in edge_id else "depuis"
            return f"Route d'accès Sud (col {col}) {direction} réseau"
    
    if 'src_north' in edge_id:
        match = re.search(r'src_north_(\d+)', edge_id)
        if match:
            col = int(match.group(1))
            direction = "vers" if "to_n" in edge_id else "depuis"
            return f"Route d'accès Nord (col {col}) {direction} réseau"
    
    if 'src_west' in edge_id:
        match = re.search(r'src_west_(\d+)', edge_id)
        if match:
            row = int(match.group(1))
            direction = "vers" if "to_n" in edge_id else "depuis"
            return f"Route d'accès Ouest (lig {row}) {direction} réseau"
    
    if 'src_east' in edge_id:
        match = re.search(r'src_east_(\d+)', edge_id)
        if match:
            row = int(match.group(1))
            direction = "vers" if "to_n" in edge_id else "depuis"
            return f"Route d'accès Est (lig {row}) {direction} réseau"
    
    # Routes internes (grille)
    match = re.match(r'e_n(\d+)_(\d+)_to_n(\d+)_(\d+)', edge_id)
    if match:
        r1, c1, r2, c2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
        
        # Direction N-S (rangée change)
        if r1 != r2:
            if c1 == 2 or c2 == 2:
                direction = "Nord" if r2 > r1 else "Sud"
                return f"🌉 Pont De Gaulle {direction} (col 2)"
            elif c1 == 3 or c2 == 3:
                direction = "Nord" if r2 > r1 else "Sud"
                return f"🌉 Pont HKB {direction} (col 3)"
            else:
                direction = "Nord" if r2 > r1 else "Sud"
                col = c1
                return f"Rue Verticale {direction} (col {col})"
        
        # Direction E-O (colonne change)
        else:
            if r1 == 2 or r2 == 2:
                direction = "Est" if c2 > c1 else "Ouest"
                return f"🛣️  Avenue Principale {direction} (lig 2)"
            elif r1 == 3 or r2 == 3:
                direction = "Est" if c2 > c1 else "Ouest"
                return f"🛣️  Boulevard Central {direction} (lig 3)"
            else:
                direction = "Est" if c2 > c1 else "Ouest"
                row = r1
                return f"Rue Horizontale {direction} (lig {row})"
    
    return edge_id


def get_road_color(edge_id: str) -> tuple:
    """
    Retourne la couleur RGB pour une arête basée sur son type.
    
    Returns:
        Tuple (R, G, B) ou None pour couleur par défaut
    """
    if 'src_' in edge_id:
        return (100, 100, 100)  # Gris foncé pour routes d'accès
    
    # Pont De Gaulle (colonne 2, N-S)
    if '_n' in edge_id and '_2_to_n' in edge_id or '_to_n' in edge_id and '_2' in edge_id:
        import re
        match = re.match(r'e_n(\d+)_(\d+)_to_n(\d+)_(\d+)', edge_id)
        if match:
            r1, c1, r2, c2 = int(match.group(1)), int(match.group(2)), int(match.group(3)), int(match.group(4))
            if (c1 == 2 or c2 == 2) and r1 != r2:
                return (255, 200, 0)  # Jaune-or pour Pont De Gaulle
    
    # Avenue Principale (rangée 2, E-O)
    if '_n2_' in edge_id and '_to_n2_' in edge_id:
        return (0, 150, 255)  # Bleu ciel pour Avenue Principale
    
    return None  # Couleur par défaut (noir)


def get_all_road_names() -> dict:
    """Retourne un dictionnaire {edge_id: road_name} pour toutes les arêtes"""
    road_names = {}
    
    # Routes d'accès
    for c in range(6):
        road_names[f"e_src_south_{c}_to_n0_{c}"] = get_road_name(f"e_src_south_{c}_to_n0_{c}")
        road_names[f"e_n0_{c}_to_src_south_{c}"] = get_road_name(f"e_n0_{c}_to_src_south_{c}")
        road_names[f"e_src_north_{c}_to_n5_{c}"] = get_road_name(f"e_src_north_{c}_to_n5_{c}")
        road_names[f"e_n5_{c}_to_src_north_{c}"] = get_road_name(f"e_n5_{c}_to_src_north_{c}")
    
    for r in range(6):
        road_names[f"e_src_west_{r}_to_n{r}_0"] = get_road_name(f"e_src_west_{r}_to_n{r}_0")
        road_names[f"e_n{r}_0_to_src_west_{r}"] = get_road_name(f"e_n{r}_0_to_src_west_{r}")
        road_names[f"e_src_east_{r}_to_n{r}_5"] = get_road_name(f"e_src_east_{r}_to_n{r}_5")
        road_names[f"e_n{r}_5_to_src_east_{r}"] = get_road_name(f"e_n{r}_5_to_src_east_{r}")
    
    # Routes internes
    for r in range(6):
        for c in range(5):
            # E-O
            road_names[f"e_n{r}_{c}_to_n{r}_{c+1}"] = get_road_name(f"e_n{r}_{c}_to_n{r}_{c+1}")
            road_names[f"e_n{r}_{c+1}_to_n{r}_{c}"] = get_road_name(f"e_n{r}_{c+1}_to_n{r}_{c}")
    
    for r in range(5):
        for c in range(6):
            # N-S
            road_names[f"e_n{r}_{c}_to_n{r+1}_{c}"] = get_road_name(f"e_n{r}_{c}_to_n{r+1}_{c}")
            road_names[f"e_n{r+1}_{c}_to_n{r}_{c}"] = get_road_name(f"e_n{r+1}_{c}_to_n{r}_{c}")
    
    return road_names
