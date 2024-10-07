#!/usr/bin/python

import subprocess
import os

# Set SUMO_HOME to the correct path in Windows
SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"

# Step 1 - Network Generation
def generateRandomSUMONet(outFile, numEdges):
    subprocess.run(['netgenerate.exe', '--rand', '-o', outFile, '--rand.iterations=' + str(numEdges), '-j', 'traffic_light', '--random'], shell=True)

def generateRandomGridSUMONet(outFile, numEdges, randomGrid):
    subprocess.run(['netgenerate.exe', '--rand', '-o', outFile, '--rand.iterations=' + str(numEdges), '-j', 'traffic_light', '--random', '--rand.grid'], shell=True)

# Step 2 - Random Trips Generation
def generateRandomTrips(netFile, outFile, vClass, nMobiles, sTime, eTime):
    subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'randomTrips.py'), '-n', netFile, '-b', str(sTime), '-e', str(eTime), '-o', outFile, '-p', str((eTime-sTime)/nMobiles), '--vehicle-class', vClass, '--random', '--random-depart', '--validate'], shell=True)
    # Move the side-product (of validate) route file (maybe not needed at all)
    subprocess.run(['move', 'routes.rou.xml', outFile[:-8] + '_routes.rou.xml'], shell=True)

# Step 3 - Routing
def generateRoutes(netFile, tripFile, outFile):
    subprocess.run(['duarouter.exe', '--net-file', netFile, '--route-files', tripFile, '--output-file', outFile], shell=True)

# Step 4 - Prepare the Config File
def generateConfigFile(netFile, routeFile, outFile):
    # Open the file for writing
    with open(outFile, 'w') as f:
        # Define the data to be written
        data = ['<configuration>', '<input>', '<net-file value=\"' + netFile + '\"/> ', '<route-files value=\"' + routeFile + '\"/>', '</input>', '</configuration>']

        # Use a for loop to write each line of data to the file
        for line in data:
            f.write(line + '\n')
    # The file is automatically closed when the 'with' block ends

# Step 5 - Run the Simulation
def runSimulation(configFile, traceFile):
    subprocess.run(['sumo.exe', '-c', configFile, '--fcd-output', traceFile], shell=True)

# Step 6 - Convert the Trace to NS2 Format
def convertTrace(traceFile, outFile):
    subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'traceExporter.py'), '--fcd-input', traceFile, '--ns2mobility-output', outFile], shell=True)

if __name__ == '__main__':

    iterations = 30
    numEdges = 5000

    vClasses = ["passenger", "bicycle"]
    nMobiles = 25
    sTime = 0
    eTime = 12000

    folder = "C:\\Users\\MONSTER\\my_data2\\random\\"
    #folder = "my_data2\\random_grid\\"

    # Create the output folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    
    for i in range(iterations):
        fname = os.path.join(folder, f"{i}_randomNet_{numEdges}")
        # Generate net file
        netFile = fname + ".net.xml"
        generateRandomSUMONet(netFile, numEdges)

        for vc in vClasses:
            # Generate trip file
            tripFile = fname + f"_{vc}_trips.rou.xml"
            generateRandomTrips(netFile, tripFile, vc, nMobiles, sTime, eTime)

            # Generate route file
            routeFile = fname + f"_{vc}_dua.rou.xml"
            generateRoutes(netFile, tripFile, routeFile)

            # Generate config file
            configFile = fname + f"_{vc}.sumocfg"
            generateConfigFile(netFile[len(folder):], routeFile[len(folder):], configFile)

            # Run SUMO simulation
            traceFile = fname + f"_{vc}_trace.xml"
            runSimulation(configFile, traceFile)

            # Convert the trace file to NS2 format
            ns2File = fname + f"_{vc}_trace.tcl"
            convertTrace(traceFile, ns2File)
