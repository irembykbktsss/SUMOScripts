#!/usr/bin/python

import osmnx as ox
import subprocess
import os

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"  # Adjust this to your SUMO installation path

# Step 1 - Download Map from OSM
def getMapFromOSM(place, dist, outDir, outFile):
    # Geocode
    lat, lng = ox.geocode(place)
    p = lat, lng

    # Get the bbox
    north, south, east, west = ox.utils_geo.bbox_from_point(p, dist)
    bbox = west, south, east, north
    bboxStr = (str(coord) for coord in bbox)
    bboxStr = ','.join(bboxStr)
    
    # Download the bbox
    subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'osmGet.py'), '--bbox=' + bboxStr, '--output-dir', outDir])

    # Rename the file
    os.rename(os.path.join(outDir, 'osm_bbox.osm.xml'), outFile)

# Step 2 - Convert OSM Map to SUMO Network
def convertOSMtoSUMONet(osmFile, netFile, stopsFile, linesFile):
    typeFile1 = os.path.join(SUMO_HOME, "data", "typemap", "osmNetconvert.typ.xml")
    typeFile2 = os.path.join(SUMO_HOME, "data", "typemap", "osmNetconvertUrbanDe.typ.xml")
    subprocess.run(['netconvert', '--type-files', typeFile1 + ',' + typeFile2, '--osm-files', osmFile, '-o', netFile, '--osm.stop-output.length', '20', '--ptstop-output', stopsFile, '--ptline-output', linesFile, '--geometry.remove', '--roundabouts.guess', '--ramps.guess', '--junctions.join', '--tls.guess-signals', '--tls.discard-simple', '--tls.join'])

# Step 3 - Find Travel Times & Create Public Transport Schedules
def generateSchedules(netFile, stopFile, linesFile, flowsFile, nMobiles, vc, sTime, eTime):
    subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'ptlines2flows.py'), '-n', netFile, '-s', stopFile, '-l', linesFile, '-o', flowsFile, '--types', vc, '--vtype-prefix', vc[0:3], '-b', str(sTime), '-e', str(eTime), '-p', str((eTime - sTime) / nMobiles), '--use-osm-routes'])

# Step 4 - Random Trips Generation
def generateRandomTrips(netFile, outFile, nMobiles, vc, sTime, eTime):
    subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'randomTrips.py'), '-n', netFile, '-b', str(sTime), '-e', str(eTime), '-p', str((eTime - sTime) / nMobiles), '-o', outFile, '--vehicle-class', vc, '--prefix', 'trip' + vc[0:3], '--random', '--random-depart', '--validate'])
    # Move the side-product (of validate) route file (maybe not needed at all)
    os.rename('routes.rou.xml', outFile[:-8] + '_routes.rou.xml')

# Step 5 - Routing
def generateRoutes(netFile, tripFile, outFile):
    subprocess.run(['duarouter', '--net-file', netFile, '--route-files', tripFile, '--output-file', outFile])

# Step 6 - Prepare the Config File
def generateConfigFile(netFile, routeFile, flowFile, outFile):
    # Open the file for writing
    with open(outFile, 'w') as f:
        # Define the data to be written
        data = ['<configuration>', '<input>', '<net-file value=\"' + netFile + '\"/> ', '<route-files value=\"' + routeFile + ',' + flowFile + '\"/>', '</input>', '</configuration>']

        # Use a for loop to write each line of data to the file
        for line in data:
            f.write(line + '\n')

# Step 7 - Run the Simulation
def runSimulation(netFile, routeFile, flowFile, stopFile, traceFile):
    subprocess.run(['sumo', '-n', netFile, '-r', routeFile, '-a', stopFile, '--fcd-output', traceFile]) 

# Step 8 - Convert the Trace to NS2 Format
def convertTrace(traceFile, outFile):
    subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'traceExporter.py'), '--fcd-input', traceFile, '--ns2mobility-output', outFile])

if __name__ == '__main__':

    iterations = 30

    places = ['Antwerp,Belgium', 'Bruges,Belgium', 'Brussels,Belgium', 'Ghent,Belgium', 'Liege,Belgium', 'Amsterdam,Netherlands', 'Eindhoven,Netherlands', 'Rotterdam,Netherlands', 'Essen,Germany', 'Bonn,Germany', 'Cologne,Germany', 'Dortmund,Germany', 'Bremen,Germany', 'Frankfurt,Germany', 'Hamburg,Germany', 'Hanover,Germany', 'Dresden,Germany', 'Stuttgart,Germany', 'Munich,Germany', 'Basel,Switzerland', 'Zürich,Switzerland', 'Vienna,Austria', 'Graz,Austria', 'Milan,Italy', 'Turin,Italy', 'Parma,Italy', 'Bologna,Italy', 'Florence,Italy', 'Rome,Italy', 'Barcelona,Spain']
    dist = 5000

    nMobiles = 100
    sTime = 0
    eTime = 12000
    vc = 'bus'
    
    folder =  "C:\Users\MONSTER\my_data2\osm-pt" 
 
    # Create the directory if it does not exist
    os.makedirs(folder, exist_ok=True)

    for i in range(iterations):
        fname = os.path.join(folder, str(i) + "_osm_bbox_" + str(dist))
        # Download OSM file
        osmFile = fname + ".osm.xml"
        getMapFromOSM(places[i], dist, folder, osmFile)

        # Generate net file
        netFile = fname + ".net.xml"
        stopsFile = fname + ".stop.xml"
        linesFile = fname + ".ptlines.xml"
        convertOSMtoSUMONet(osmFile, netFile, stopsFile, linesFile)

        # Find travel times and create PT schedules
        flowsFile = fname + ".flows.rou.xml"
        generateSchedules(netFile, stopsFile, linesFile, flowsFile, nMobiles, vc, sTime, eTime)
        
        # Generate trip file
        tripFile = fname + ".trips.rou.xml"
        generateRandomTrips(netFile, tripFile, nMobiles, vc, sTime, eTime)

        # Generate route file
        routeFile = fname + ".dua.rou.xml"
        generateRoutes(netFile, tripFile, routeFile)
            
        # Generate config file
        configFile = fname + ".sumocfg"
        generateConfigFile(netFile[len(folder):], routeFile[len(folder):], flowsFile[len(folder):], configFile)

        # Run SUMO simulation
        traceFile = fname + "_trace.xml"
        runSimulation(netFile, routeFile, flowsFile, stopsFile, traceFile)

        # Convert the trace file to NS2 format
        ns2File = fname + "_trace.tcl"
        convertTrace(traceFile, ns2File)
