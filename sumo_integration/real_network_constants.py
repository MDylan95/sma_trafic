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
BBOX_YOPOUGON  = (-4.070, 5.320, -4.010, 5.380)   # Ouest - origine flux heure de pointe
BBOX_ABOBO     = (-4.030, 5.410, -3.970, 5.470)   # Nord - origine flux heure de pointe
BBOX_PLATEAU   = (-4.020, 5.300, -3.970, 5.360)   # Centre - zone d'affaires (CBD)
BBOX_COCODY    = (-3.990, 5.330, -3.950, 5.420)   # Est - destination flux heure de pointe
