"""
Constantes du réseau réel d'Abidjan (généré automatiquement par import_real_abidjan.py).
Utilisées par sumo_connector.py et incident.py.
"""

# Fichiers réseau réel
REAL_NET_FILE   = "abidjan_real.net.xml"
REAL_SUMOCFG    = "abidjan_real.sumocfg"
REAL_ROUTES     = "routes_real.rou.xml"

# Edges du Pont De Gaulle (à bloquer lors du scénario incident)
PONT_DE_GAULLE_EDGES = ['307221092', '333112567']

# Edges du Pont HKB Félix Houphouët-Boigny (route alternative)
PONT_HKB_EDGES = ['-1134018274#0', '-1134018274#1', '-1134018274#2', '-1134019376', '-1134019377#0', '-294636279#0', '22703950', '295474302', '30656596']

# ---------------------------------------------------------------------------
# Zones géographiques (bbox en coordonnées GPS : lon_min, lat_min, lon_max, lat_max)
# origBoundary du réseau : -4.074043,5.283383,-3.923975,5.441035
# ---------------------------------------------------------------------------
BBOX_YOPOUGON  = (-4.074, 5.310, -4.000, 5.380)   # Ouest
BBOX_ABOBO     = (-4.000, 5.370, -3.924, 5.440)   # Nord
BBOX_PLATEAU   = (-4.030, 5.295, -3.985, 5.335)   # Centre
BBOX_COCODY    = (-3.985, 5.330, -3.924, 5.430)   # Est
