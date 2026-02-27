"""
Génère le réseau SUMO correspondant à la grille de simulation Mesa.
Crée un réseau en grille représentant le district d'Abidjan (Plateau/Cocody/Yopougon).
"""
import os
import subprocess
import sys
import math


def generate_nodes_xml(filepath: str, rows: int = 6, cols: int = 6, spacing: float = 500.0):
    """
    Génère le fichier .nod.xml (nœuds/intersections).
    
    Args:
        filepath: Chemin du fichier de sortie
        rows: Nombre de rangées d'intersections
        cols: Nombre de colonnes d'intersections
        spacing: Espacement entre intersections (mètres)
    """
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<nodes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                 'xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/nodes_file.xsd">')
    
    for r in range(rows):
        for c in range(cols):
            node_id = f"n{r}_{c}"
            x = c * spacing
            y = r * spacing
            node_type = "traffic_light"
            lines.append(f'    <node id="{node_id}" x="{x:.1f}" y="{y:.1f}" type="{node_type}"/>')
    
    # Nœuds d'entrée/sortie sur les bords (pour générer du trafic)
    for c in range(cols):
        # Bord sud (entrée)
        lines.append(f'    <node id="src_south_{c}" x="{c * spacing:.1f}" y="{-spacing:.1f}" type="priority"/>')
        # Bord nord (sortie)
        lines.append(f'    <node id="src_north_{c}" x="{c * spacing:.1f}" y="{rows * spacing:.1f}" type="priority"/>')
    
    for r in range(rows):
        # Bord ouest (entrée)
        lines.append(f'    <node id="src_west_{r}" x="{-spacing:.1f}" y="{r * spacing:.1f}" type="priority"/>')
        # Bord est (sortie)
        lines.append(f'    <node id="src_east_{r}" x="{cols * spacing:.1f}" y="{r * spacing:.1f}" type="priority"/>')
    
    lines.append('</nodes>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"✅ Nœuds générés: {filepath} ({rows * cols} intersections + {2*(rows+cols)} entrées/sorties)")


def _get_edge_name(edge_id: str, r1: int, c1: int, r2: int, c2: int, 
                    rows: int, cols: int) -> str:
    """Retourne le nom descriptif d'une arête interne du réseau."""
    # Direction N-S (rangée change)
    if r1 != r2:
        direction = "Nord" if r2 > r1 else "Sud"
        if c1 == 2:
            return f"Pont De Gaulle {direction}"
        elif c1 == 3:
            return f"Pont HKB {direction}"
        elif c1 == 0:
            return f"Rue Yopougon {direction}"
        elif c1 == 1:
            return f"Rue Adjame {direction}"
        elif c1 == 4:
            return f"Rue Cocody {direction}"
        elif c1 == 5:
            return f"Rue Bingerville {direction}"
        else:
            return f"Rue Verticale col{c1} {direction}"
    # Direction E-O (colonne change)
    else:
        direction = "Est" if c2 > c1 else "Ouest"
        if r1 == 0:
            return f"Bd Lagunaire {direction}"
        elif r1 == 1:
            return f"Rue Commerce {direction}"
        elif r1 == 2:
            return f"Avenue Principale {direction}"
        elif r1 == 3:
            return f"Bd Republique {direction}"
        elif r1 == 4:
            return f"Rue Universite {direction}"
        elif r1 == 5:
            return f"Bd Nord {direction}"
        else:
            return f"Rue Horizontale lig{r1} {direction}"


def generate_edges_xml(filepath: str, rows: int = 6, cols: int = 6, 
                        speed: float = 13.89, num_lanes: int = 2):
    """
    Génère le fichier .edg.xml (routes/arêtes) avec noms descriptifs.
    
    Args:
        filepath: Chemin du fichier de sortie
        rows: Nombre de rangées
        cols: Nombre de colonnes
        speed: Vitesse max en m/s (50 km/h par défaut)
        num_lanes: Nombre de voies par direction
    """
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<edges xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
                 'xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/edges_file.xsd">')
    
    # Arêtes horizontales (est-ouest)
    for r in range(rows):
        for c in range(cols - 1):
            from_id = f"n{r}_{c}"
            to_id = f"n{r}_{c+1}"
            # Direction est
            name_e = _get_edge_name(f"e_{from_id}_to_{to_id}", r, c, r, c+1, rows, cols)
            lines.append(f'    <edge id="e_{from_id}_to_{to_id}" from="{from_id}" to="{to_id}" '
                        f'numLanes="{num_lanes}" speed="{speed:.2f}" name="{name_e}"/>')
            # Direction ouest
            name_w = _get_edge_name(f"e_{to_id}_to_{from_id}", r, c+1, r, c, rows, cols)
            lines.append(f'    <edge id="e_{to_id}_to_{from_id}" from="{to_id}" to="{from_id}" '
                        f'numLanes="{num_lanes}" speed="{speed:.2f}" name="{name_w}"/>')
    
    # Arêtes verticales (nord-sud)
    for r in range(rows - 1):
        for c in range(cols):
            from_id = f"n{r}_{c}"
            to_id = f"n{r+1}_{c}"
            # Direction nord
            name_n = _get_edge_name(f"e_{from_id}_to_{to_id}", r, c, r+1, c, rows, cols)
            lines.append(f'    <edge id="e_{from_id}_to_{to_id}" from="{from_id}" to="{to_id}" '
                        f'numLanes="{num_lanes}" speed="{speed:.2f}" name="{name_n}"/>')
            # Direction sud
            name_s = _get_edge_name(f"e_{to_id}_to_{from_id}", r+1, c, r, c, rows, cols)
            lines.append(f'    <edge id="e_{to_id}_to_{from_id}" from="{to_id}" to="{from_id}" '
                        f'numLanes="{num_lanes}" speed="{speed:.2f}" name="{name_s}"/>')
    
    # Arêtes d'entrée/sortie — bord sud
    for c in range(cols):
        lines.append(f'    <edge id="e_src_south_{c}_to_n0_{c}" from="src_south_{c}" to="n0_{c}" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Acces Sud {c}"/>')
        lines.append(f'    <edge id="e_n0_{c}_to_src_south_{c}" from="n0_{c}" to="src_south_{c}" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Sortie Sud {c}"/>')
    
    # Bord nord
    for c in range(cols):
        last_row = rows - 1
        lines.append(f'    <edge id="e_src_north_{c}_to_n{last_row}_{c}" from="src_north_{c}" to="n{last_row}_{c}" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Acces Nord {c}"/>')
        lines.append(f'    <edge id="e_n{last_row}_{c}_to_src_north_{c}" from="n{last_row}_{c}" to="src_north_{c}" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Sortie Nord {c}"/>')
    
    # Bord ouest
    for r in range(rows):
        lines.append(f'    <edge id="e_src_west_{r}_to_n{r}_0" from="src_west_{r}" to="n{r}_0" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Acces Ouest {r}"/>')
        lines.append(f'    <edge id="e_n{r}_0_to_src_west_{r}" from="n{r}_0" to="src_west_{r}" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Sortie Ouest {r}"/>')
    
    # Bord est
    for r in range(rows):
        last_col = cols - 1
        lines.append(f'    <edge id="e_src_east_{r}_to_n{r}_{last_col}" from="src_east_{r}" to="n{r}_{last_col}" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Acces Est {r}"/>')
        lines.append(f'    <edge id="e_n{r}_{last_col}_to_src_east_{r}" from="n{r}_{last_col}" to="src_east_{r}" '
                    f'numLanes="{num_lanes}" speed="{speed:.2f}" name="Sortie Est {r}"/>')
    
    lines.append('</edges>')
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    total_edges = 2 * ((rows * (cols-1)) + ((rows-1) * cols)) + 2 * 2 * (rows + cols)
    print(f"✅ Arêtes générées: {filepath} ({total_edges} arêtes avec noms)")


def generate_type_xml(filepath: str):
    """Génère le fichier de types de véhicules (ne remplace pas si déjà existant)"""
    if os.path.exists(filepath):
        print(f"⏭️  Types de véhicules existants conservés: {filepath}")
        return
    
    content = """<?xml version="1.0" encoding="UTF-8"?>
<additional xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/additional_file.xsd">
    
    <!-- Véhicule standard (bleu) -->
    <vType id="standard" accel="2.0" decel="4.0" sigma="0.5" 
           length="5" width="3" maxSpeed="13.89" color="0,100,255"
           guiShape="passenger"/>
    
    <!-- Ambulance (rouge vif) -->
    <vType id="ambulance" accel="3.0" decel="5.0" sigma="0.3" 
           length="6" width="3" maxSpeed="22.22" color="255,0,0"
           guiShape="passenger"/>
    
    <!-- Bus SOTRA (vert) -->
    <vType id="bus_sotra" accel="1.5" decel="3.0" sigma="0.5" 
           length="12" width="4" maxSpeed="11.11" color="0,200,0"
           guiShape="bus"/>
    
    <!-- Pompier (orange) -->
    <vType id="pompier" accel="2.5" decel="4.5" sigma="0.3" 
           length="8" width="3" maxSpeed="19.44" color="255,100,0"
           guiShape="passenger"/>
    
    <!-- Police (jaune) -->
    <vType id="police" accel="3.0" decel="5.0" sigma="0.3" 
           length="5" width="3" maxSpeed="22.22" color="255,255,0"
           guiShape="passenger"/>
    
</additional>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Types de véhicules générés: {filepath}")


def generate_sumocfg(filepath: str, net_file: str, route_file: str, 
                     additional_file: str, begin: int = 0, end: int = 3600):
    """Génère le fichier de configuration SUMO"""
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">
    
    <input>
        <net-file value="{net_file}"/>
        <route-files value="{route_file}"/>
        <additional-files value="{additional_file}"/>
    </input>
    
    <time>
        <begin value="{begin}"/>
        <end value="{end}"/>
        <step-length value="1.0"/>
    </time>
    
    <processing>
        <time-to-teleport value="-1"/>
        <collision.action value="warn"/>
    </processing>
    
    <gui_only>
        <gui-settings-file value="gui_settings.xml"/>
    </gui_only>
    
</configuration>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Configuration SUMO générée: {filepath}")


def generate_gui_settings(filepath: str):
    """Génère les paramètres d'affichage SUMO-GUI (ne remplace pas si déjà existant)"""
    if os.path.exists(filepath):
        print(f"⏭️  Paramètres GUI existants conservés: {filepath}")
        return
    
    content = """<?xml version="1.0" encoding="UTF-8"?>
<viewsettings>
    <scheme name="real world"/>
    <viewport x="1250.00" y="1250.00" zoom="100.00"/>
    <delay value="100"/>
</viewsettings>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Paramètres GUI générés: {filepath}")


def generate_empty_routes(filepath: str):
    """Génère un fichier de routes vide (les véhicules seront ajoutés via TraCI)"""
    content = """<?xml version="1.0" encoding="UTF-8"?>
<routes xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/routes_file.xsd">
</routes>
"""
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"✅ Fichier de routes vide généré: {filepath}")


def build_network(sumo_dir: str):
    """Construit le réseau SUMO avec netconvert"""
    nod_file = os.path.join(sumo_dir, "abidjan.nod.xml")
    edg_file = os.path.join(sumo_dir, "abidjan.edg.xml")
    net_file = os.path.join(sumo_dir, "abidjan.net.xml")
    
    cmd = [
        "netconvert",
        "--node-files", nod_file,
        "--edge-files", edg_file,
        "--output-file", net_file,
        "--tls.default-type", "static",
        "--tls.cycle.time", "60",
        "--no-turnarounds", "true"
    ]
    
    print(f"\n🔧 Construction du réseau SUMO...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ Réseau SUMO construit: {net_file}")
        else:
            print(f"❌ Erreur netconvert: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ netconvert non trouvé. Vérifiez que SUMO est dans le PATH.")
        return False
    
    return True


def main():
    """Génère tous les fichiers SUMO"""
    sumo_dir = os.path.dirname(os.path.abspath(__file__))
    
    print("=" * 60)
    print("🚗 GÉNÉRATION DU RÉSEAU SUMO - Abidjan")
    print("=" * 60)
    
    # Paramètres de la grille (6x6 = 36 intersections, espacement 500m = zone 2.5km x 2.5km)
    rows, cols = 6, 6
    spacing = 500.0
    
    # 1. Générer les nœuds
    generate_nodes_xml(os.path.join(sumo_dir, "abidjan.nod.xml"), rows, cols, spacing)
    
    # 2. Générer les arêtes
    generate_edges_xml(os.path.join(sumo_dir, "abidjan.edg.xml"), rows, cols)
    
    # 3. Générer les types de véhicules
    generate_type_xml(os.path.join(sumo_dir, "vtypes.add.xml"))
    
    # 4. Générer les routes vides
    generate_empty_routes(os.path.join(sumo_dir, "routes.rou.xml"))
    
    # 5. Générer les paramètres GUI
    generate_gui_settings(os.path.join(sumo_dir, "gui_settings.xml"))
    
    # 6. Construire le réseau
    success = build_network(sumo_dir)
    
    if success:
        # 7. Générer la configuration SUMO
        generate_sumocfg(
            os.path.join(sumo_dir, "abidjan.sumocfg"),
            net_file="abidjan.net.xml",
            route_file="routes.rou.xml",
            additional_file="vtypes.add.xml"
        )
        
        print("\n" + "=" * 60)
        print("✅ Tous les fichiers SUMO générés avec succès!")
        print(f"📂 Répertoire: {sumo_dir}")
        print("\nPour lancer SUMO-GUI manuellement:")
        print(f"  sumo-gui -c {os.path.join(sumo_dir, 'abidjan.sumocfg')}")
        print("=" * 60)
    else:
        print("\n❌ Échec de la génération du réseau")
    
    return success


if __name__ == "__main__":
    main()
