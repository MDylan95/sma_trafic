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
PONT_HKB_EDGES = ['1135493394#0', '118814739#0', '147061723#3', '22703950', '22703950-AddedOffRampEdge', '295474302', '295474302-AddedOnRampEdge', '30656596', '326163564#0', '326249232#2', '366285686#0', '366285687', '392464982', '392464983', '392474803#0', '392474803#1', '392474808', '392474812#0', '392474816#0', '392474816#4', '392474819#0', '392474819#2', '392475751', '397685898#0', '397722081', '397722082#0', '397722082#2', '404096045', '404096053', '404096055', '404096060', '404096064#0', '404105137', '404105143#0', '404105148#0', '404105148#1', '737719599#0', '766696517#0']

# Zones géographiques (bbox en coordonnées GPS)
# Format: (lon_min, lat_min, lon_max, lat_max)
# BBOX recalibrées pour correspondre aux limites réelles du réseau OSM importé
BBOX_YOPOUGON  = (-4.0595, 5.3450, -4.0114, 5.3634)   # Ouest - origine flux heure de pointe
BBOX_ABOBO     = (-4.0500, 5.3634, -3.9500, 5.3909)   # Nord - origine flux heure de pointe
BBOX_PLATEAU   = (-4.0400, 5.2991, -3.9800, 5.3450)   # Sud/Centre - zone d'affaires (CBD)
BBOX_COCODY    = (-3.9900, 5.3300, -3.9500, 5.3909)   # Est - destination alternative
