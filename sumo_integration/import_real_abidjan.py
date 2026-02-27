"""
Script d'import de la carte réelle d'Abidjan depuis OpenStreetMap.

Zone couverte (conforme au cahier des charges) :
  - Le Plateau (CBD)
  - Pont De Gaulle  (scénario incident)
  - Pont HKB        (route alternative)
  - Yopougon/Abobo  (origine flux heure de pointe)
  - Cocody/Adjamé   (destination flux heure de pointe)

Usage :
    python sumo_integration/import_real_abidjan.py
"""
import os
import sys
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

# Chemin vers les outils SUMO
SUMO_TOOLS = Path(r"C:\Program Files (x86)\Eclipse\Sumo\tools")

# ---------------------------------------------------------------------------
# Coordonnées GPS de la zone d'Abidjan pertinente pour le projet
# Format osmGet.py : west,south,east,north  (lon_min,lat_min,lon_max,lat_max)
# Zone réduite centrée sur Plateau + ponts pour éviter timeouts (fichier ~5 Mo)
# ---------------------------------------------------------------------------
BBOX_STR = "-4.050,5.310,-3.970,5.380"  # Plateau + Pont De Gaulle + Pont HKB

SCRIPT_DIR  = Path(__file__).parent.resolve()
OSM_FILE    = SCRIPT_DIR / "abidjan_real.osm.xml"
NET_FILE    = SCRIPT_DIR / "abidjan_real.net.xml"
SUMOCFG     = SCRIPT_DIR / "abidjan_real.sumocfg"
ROUTES_FILE = SCRIPT_DIR / "routes_real.rou.xml"


# ---------------------------------------------------------------------------
# Étape 1 : Télécharger les données OSM via osmGet.py (outil SUMO officiel)
# osmGet.py formate correctement les données pour netconvert
# ---------------------------------------------------------------------------
def download_osm():
    if OSM_FILE.exists():
        size_mb = OSM_FILE.stat().st_size / 1_048_576
        print(f"[OK] Fichier OSM déjà présent : {OSM_FILE.name} ({size_mb:.1f} Mo)")
        return

    print("[1/4] Téléchargement OSM via osmGet.py (outil officiel SUMO)...")
    
    # Créer un fichier de configuration pour osmGet.py (évite problèmes avec virgules)
    config_file = SCRIPT_DIR / "osmget.config"
    config_content = f"""<configuration>
    <bbox value="{BBOX_STR}"/>
    <prefix value="abidjan_real"/>
    <output-dir value="{SCRIPT_DIR}"/>
</configuration>
"""
    config_file.write_text(config_content, encoding="utf-8")
    
    osmget = SUMO_TOOLS / "osmGet.py"
    result = subprocess.run(
        [sys.executable, str(osmget), "-c", str(config_file)],
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    
    config_file.unlink()  # Supprimer le fichier de config temporaire
    
    if result.stdout:
        print(f"    STDOUT osmGet.py:\n{result.stdout}")
    if result.stderr:
        print(f"    STDERR osmGet.py:\n{result.stderr}")
    
    if result.returncode != 0:
        print(f"[ERR] osmGet.py a échoué (code {result.returncode})")
        print("\n[SOLUTION] Téléchargement manuel :")
        print(f"  1. Allez sur https://www.openstreetmap.org/export")
        print(f"  2. Sélectionnez la zone : {BBOX_STR}")
        print(f"  3. Cliquez 'Export' et sauvegardez sous :")
        print(f"     {OSM_FILE}")
        print(f"  4. Relancez ce script\n")
        sys.exit(1)

    # osmGet.py génère abidjan_real_bbox.osm.xml — le renommer
    generated = SCRIPT_DIR / "abidjan_real_bbox.osm.xml"
    if generated.exists():
        generated.rename(OSM_FILE)
    elif not OSM_FILE.exists():
        # Chercher tout fichier .osm.xml généré
        candidates = list(SCRIPT_DIR.glob("abidjan_real*.osm.xml"))
        if candidates:
            candidates[0].rename(OSM_FILE)
        else:
            print("[ERR] Fichier OSM introuvable après osmGet.py")
            print(f"    Fichiers générés dans {SCRIPT_DIR}:")
            for f in SCRIPT_DIR.glob("abidjan_real*"):
                print(f"      - {f.name}")
            sys.exit(1)

    size_mb = OSM_FILE.stat().st_size / 1_048_576
    print(f"[OK] Téléchargé : {OSM_FILE.name} ({size_mb:.1f} Mo)")


# ---------------------------------------------------------------------------
# Étape 2 : Convertir OSM → réseau SUMO avec osmBuild.py (outil SUMO officiel)
# osmBuild.py encapsule netconvert avec les bons paramètres pour OSM
# ---------------------------------------------------------------------------
def convert_osm_to_sumo():
    if NET_FILE.exists():
        size_mb = NET_FILE.stat().st_size / 1_048_576
        print(f"[OK] Réseau SUMO déjà converti : {NET_FILE.name} ({size_mb:.1f} Mo)")
        return

    print("[2/4] Conversion OSM → réseau SUMO via osmBuild.py...")
    osmbuild = SUMO_TOOLS / "osmBuild.py"

    result = subprocess.run(
        [sys.executable, str(osmbuild),
         "--osm-file",        str(OSM_FILE),
         "--prefix",          "abidjan_real",
         "--output-directory", str(SCRIPT_DIR),
         "--vehicle-classes", "passenger"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(SCRIPT_DIR)
    )
    
    # Afficher toute la sortie pour diagnostic
    if result.stdout:
        print(f"    STDOUT osmBuild.py:\n{result.stdout}")
    if result.stderr:
        print(f"    STDERR osmBuild.py:\n{result.stderr}")
    
    if result.returncode != 0:
        print(f"[ERR] osmBuild.py a échoué (code {result.returncode})")
        sys.exit(1)

    # osmBuild génère abidjan_real.net.xml dans le répertoire courant
    generated_net = SCRIPT_DIR / "abidjan_real.net.xml"
    if not generated_net.exists():
        # Chercher tout .net.xml généré
        candidates = list(SCRIPT_DIR.glob("abidjan_real*.net.xml"))
        if candidates:
            print(f"[OK] Réseau : {candidates[0].name}")
            if candidates[0] != NET_FILE:
                candidates[0].rename(NET_FILE)
        else:
            print(f"[ERR] Fichier .net.xml introuvable après osmBuild.py")
            print(f"    Fichiers générés dans {SCRIPT_DIR}:")
            for f in SCRIPT_DIR.glob("abidjan_real*"):
                print(f"      - {f.name}")
            sys.exit(1)

    size_mb = NET_FILE.stat().st_size / 1_048_576
    print(f"[OK] Réseau converti : {NET_FILE.name} ({size_mb:.1f} Mo)")


# ---------------------------------------------------------------------------
# Étape 3 : Identifier les edges du Pont De Gaulle et Pont HKB
# ---------------------------------------------------------------------------
def find_bridge_edges():
    """
    Parse le .net.xml pour trouver les edges portant le nom
    'Pont De Gaulle', 'Pont Félix Houphouët-Boigny' (HKB), etc.
    Retourne deux listes d'IDs d'edges.
    """
    print("[3/4] Identification des edges des deux ponts...")

    tree = ET.parse(NET_FILE)
    root = tree.getroot()

    pdg_edges   = []  # Pont De Gaulle
    hkb_edges   = []  # Pont HKB / Félix Houphouët-Boigny
    pdg_keywords = ["gaulle", "de gaulle"]
    hkb_keywords = ["hkb", "houphouet", "houphouët", "felix", "félix", "boigny"]

    for edge in root.findall("edge"):
        eid  = edge.get("id", "")
        name = edge.get("name", "").lower()
        # Ignorer edges internes SUMO
        if eid.startswith(":"):
            continue
        if any(k in name for k in pdg_keywords):
            pdg_edges.append(eid)
        elif any(k in name for k in hkb_keywords):
            hkb_edges.append(eid)

    print(f"    Pont De Gaulle : {len(pdg_edges)} edges trouvés → {pdg_edges[:4]}")
    print(f"    Pont HKB       : {len(hkb_edges)} edges trouvés → {hkb_edges[:4]}")

    if not pdg_edges:
        print("    [AVERTISSEMENT] Aucun edge nommé 'Pont De Gaulle' trouvé.")
        print("    Les noms OSM seront listés dans bridge_edges_report.txt pour identification manuelle.")
        _dump_bridge_candidates(root)

    return pdg_edges, hkb_edges


def _dump_bridge_candidates(root):
    """Exporte tous les edges avec nom contenant 'pont' ou 'bridge'."""
    report = SCRIPT_DIR / "bridge_edges_report.txt"
    lines = ["ID_EDGE\tNOM\n"]
    for edge in root.findall("edge"):
        eid  = edge.get("id", "")
        name = edge.get("name", "")
        if eid.startswith(":"):
            continue
        if any(k in name.lower() for k in ["pont", "bridge", "lagune", "gaulle", "hkb", "houphouet"]):
            lines.append(f"{eid}\t{name}\n")
    report.write_text("".join(lines), encoding="utf-8")
    print(f"    Rapport sauvegardé : {report.name}")


# ---------------------------------------------------------------------------
# Étape 4 : Générer les fichiers de configuration SUMO
# ---------------------------------------------------------------------------
def generate_sumocfg(pdg_edges, hkb_edges):
    print("[4/4] Génération des fichiers de configuration SUMO...")

    # --- routes_real.rou.xml : fichier minimal (les routes sont ajoutées par TraCI) ---
    routes_xml = '<?xml version="1.0" encoding="UTF-8"?>\n<routes>\n</routes>\n'
    ROUTES_FILE.write_text(routes_xml, encoding="utf-8")

    # --- abidjan_real.sumocfg ---
    sumocfg_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:noNamespaceSchemaLocation="http://sumo.dlr.de/xsd/sumoConfiguration.xsd">

    <input>
        <net-file value="abidjan_real.net.xml"/>
        <route-files value="routes_real.rou.xml"/>
        <additional-files value="vtypes.add.xml"/>
    </input>

    <time>
        <begin value="0"/>
        <end value="7200"/>
        <step-length value="1.0"/>
    </time>

    <processing>
        <time-to-teleport value="-1"/>
        <collision.action value="warn"/>
        <ignore-junction-blocker value="10"/>
    </processing>

    <gui_only>
        <gui-settings-file value="gui_settings.xml"/>
    </gui_only>

</configuration>
"""
    SUMOCFG.write_text(sumocfg_xml, encoding="utf-8")

    # --- Fichier Python de constantes pour le projet ---
    const_file = SCRIPT_DIR / "real_network_constants.py"
    pdg_list   = repr(pdg_edges)
    hkb_list   = repr(hkb_edges)
    constants  = f'''"""
Constantes du réseau réel d\'Abidjan (généré automatiquement par import_real_abidjan.py).
Utilisées par sumo_connector.py et incident.py.
"""

# Fichiers réseau réel
REAL_NET_FILE   = "abidjan_real.net.xml"
REAL_SUMOCFG    = "abidjan_real.sumocfg"
REAL_ROUTES     = "routes_real.rou.xml"

# Edges du Pont De Gaulle (à bloquer lors du scénario incident)
PONT_DE_GAULLE_EDGES = {pdg_list}

# Edges du Pont HKB Félix Houphouët-Boigny (route alternative)
PONT_HKB_EDGES = {hkb_list}

# Zones géographiques (bbox en coordonnées GPS)
BBOX_YOPOUGON  = (-4.070, 5.320, -4.010, 5.380)   # origine flux heure de pointe
BBOX_PLATEAU   = (-4.020, 5.300, -3.970, 5.360)   # zone centrale / CBD
BBOX_COCODY    = (-3.990, 5.330, -3.950, 5.420)   # destination flux heure de pointe
'''
    const_file.write_text(constants, encoding="utf-8")

    print(f"[OK] {SUMOCFG.name}")
    print(f"[OK] {ROUTES_FILE.name}")
    print(f"[OK] {const_file.name}")


# ---------------------------------------------------------------------------
# Étape 5 : Mettre à jour sumo_connector.py pour utiliser le vrai réseau
# ---------------------------------------------------------------------------
def patch_sumo_connector():
    connector = SCRIPT_DIR / "sumo_connector.py"
    text = connector.read_text(encoding="utf-8")

    old = '"abidjan.sumocfg"'
    new = '"abidjan_real.sumocfg"'
    if new in text:
        print("[OK] sumo_connector.py déjà configuré pour le réseau réel.")
        return

    if old not in text:
        print("[WARN] Impossible de patcher sumo_connector.py automatiquement.")
        print("       Changez manuellement 'abidjan.sumocfg' → 'abidjan_real.sumocfg'")
        return

    text = text.replace(old, new)
    connector.write_text(text, encoding="utf-8")
    print("[OK] sumo_connector.py mis à jour (abidjan_real.sumocfg)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    print("=" * 60)
    print(" Import réseau réel Abidjan (OSM → SUMO)")
    print("=" * 60)
    print(f" Zone : {BBOX_STR}  (west,south,east,north)")
    print()

    download_osm()
    convert_osm_to_sumo()
    pdg_edges, hkb_edges = find_bridge_edges()
    generate_sumocfg(pdg_edges, hkb_edges)
    patch_sumo_connector()

    print()
    print("=" * 60)
    print(" TERMINÉ")
    print("=" * 60)
    print(f"  Réseau réel : {NET_FILE.name}")
    print(f"  Config SUMO : {SUMOCFG.name}")
    print()
    print(" Prochaine étape :")
    print("   python main.py --sumo --sumo-interactive --scenario incident --steps 500")
    print()
    if not (pdg_edges and hkb_edges):
        print(" [!] Certains ponts n'ont pas été trouvés automatiquement.")
        print(f"     Consultez bridge_edges_report.txt pour les identifier")
        print("     et mettez à jour PONT_DE_GAULLE_EDGES / PONT_HKB_EDGES")
        print("     dans sumo_integration/real_network_constants.py")


if __name__ == "__main__":
    main()
