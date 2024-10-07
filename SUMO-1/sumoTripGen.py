#!/usr/bin/python

import osmnx as ox
import subprocess
import os
import shutil

# Set SUMO_HOME to the correct path in Windows
SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"

# Step 1 - Download Map from OSM
def getMapFromOSM(place, dist, outDir, outFile):
    try:
        # Geocode
        p = ox.geocode(place)
    except Exception as e:
        print(f"Error geocoding place '{place}': {e}")
        return

    # Get the bbox
    north, south, east, west = ox.utils_geo.bbox_from_point(p, dist)
    bbox = west, south, east, north
    bboxStr = ','.join(str(coord) for coord in bbox)
    
    # Download the bbox
    try:
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'osmGet.py'), '--bbox=' + bboxStr, '--output-dir', outDir], check=True)
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if e.stderr else "No error message provided."
        print(f"Error downloading OSM data for {place}: {error_message}")
        return

    # Rename the file using Python shutil for Windows compatibility
    original_file = os.path.join(outDir, 'osm_bbox.osm.xml')
    new_file = os.path.join(outDir, outFile)

    if os.path.exists(original_file):
        try:
            shutil.move(original_file, new_file)
            print(f'Renamed {original_file} to {new_file}')
        except Exception as e:
            print(f"Error renaming file: {e}")
    else:
        print(f'Warning: {original_file} not found. Please check the download process.')

# Step 2 - Convert OSM Map to SUMO Network
def generateSUMONetFromOSM(osmFile, outDir, iteration):
    print(f"Generating SUMO network from {osmFile}...")
    try:
        osm_build_script = os.path.join(SUMO_HOME, "tools", "osmBuild.py")
        command = f'python "{osm_build_script}" --osm-file "{osmFile}" --netconvert-options=--tls.ignore-internal-junction-jam --output-directory "{outDir.rstrip("\\")}"'

        print(f"Running command: {command}")  # Debugging output

        result = subprocess.run(command, check=True, shell=True, capture_output=True)

        print("Standard Output:", result.stdout.decode())
        print("Standard Error:", result.stderr.decode())

        # Oluşan dosyanın adını belirle
        original_net_file = 'osm.net.xml'  # OSM dosyasından oluşturulan ağ dosyasının varsayılan adı
        new_net_file = os.path.join(outDir, f'{iteration}_osm_bbox_{5000}_osm.net.xml')  # Yeni dosya adı

        # Dosyanın varlığını kontrol et ve yeniden adlandır
        if os.path.exists(os.path.join(outDir, original_net_file)):
            shutil.move(os.path.join(outDir, original_net_file), new_net_file)
            print(f"Generated network file: {new_net_file}")

        # Burada oluşan 'osm.netccfg' dosyasının adını da değiştiriyoruz
        original_cfg_file = 'osm.netccfg'  # OSM ağ yapılandırma dosyasının varsayılan adı
        new_cfg_file = os.path.join(outDir, f'{iteration}_osm_bbox_{5000}_osm.netccfg')  # Yeni dosya adı

        # CFG dosyasının varlığını kontrol et ve yeniden adlandır
        if os.path.exists(os.path.join(outDir, original_cfg_file)):
            shutil.move(os.path.join(outDir, original_cfg_file), new_cfg_file)
            print(f"Generated config file: {new_cfg_file}")
        else:
            print(f"Warning: Config file not found at expected location: {original_cfg_file}")

    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if e.stderr else "No error message provided."
        print(f"Error generating SUMO network from {osmFile}: {error_message}")

# Step 3 - Extract the Polygons from the OSM file
def extractPolygonsFromOSM(osmFile, netFile, typeFile, outFile):
    if not os.path.exists(netFile):
        print(f"Error: Network file {netFile} does not exist.")
        return

    try:
        subprocess.run(['polyconvert', '--net-file', netFile, '--osm-files', osmFile, '--type-file', typeFile, '-o', outFile], check=True)
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if e.stderr else "No error message provided."
        print(f"Error extracting polygons from {osmFile}: {error_message}")

# Step 4 - Random Trips Generation
def generateRandomTrips(netFile, outFile, vClass, nMobiles, sTime, eTime):
    try:
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'randomTrips.py'), '-n', netFile, '-b', str(sTime), '-e', str(eTime), '-o', outFile, '-p', str((eTime - sTime) / nMobiles), '--vehicle-class', vClass, '--random', '--random-depart', '--validate'], check=True)
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if e.stderr else "No error message provided."
        print(f"Error generating random trips: {error_message}")

# Step 5 - Routing
def generateRoutes(netFile, tripFile, outFile):
    try:
        subprocess.run(['duarouter', '--net-file', netFile, '--route-files', tripFile, '--output-file', outFile], check=True)
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if e.stderr else "No error message provided."
        print(f"Error generating routes for {tripFile}: {error_message}")

# Step 6 - Prepare the Config File
def generateConfigFile(netFile, routeFile, polyFile, outFile):
    try:
        with open(outFile, 'w') as f:
            data = [
                '<configuration>',
                '<input>',
                f'<net-file value="{netFile}"/>',
                f'<route-files value="{routeFile}"/>',
                f'<additional-files value="{polyFile}"/>',
                '</input>',
                '</configuration>'
            ]
            for line in data:
                f.write(line + '\n')
    except Exception as e:
        print(f"Error writing config file {outFile}: {e}")

# Step 7 - Run the Simulation
def runSimulation(configFile, traceFile):
    try:
        subprocess.run(['sumo', '-c', configFile, '--fcd-output', traceFile], check=True)
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if e.stderr else "No error message provided."
        print(f"Error running SUMO simulation: {error_message}")

# Step 8 - Convert the Trace to NS2 Format
def convertTrace(traceFile, outFile):
    try:
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'traceExporter.py'), '--fcd-input', traceFile, '--ns2mobility-output', outFile], check=True)
    except subprocess.CalledProcessError as e:
        error_message = e.stderr.decode() if e.stderr else "No error message provided."
        print(f"Error converting trace file {traceFile} to NS2 format: {error_message}")

if __name__ == '__main__':
    iterations = 30

    places = [
        'Antwerp,Belgium', 'Bruges,Belgium', 'Brussels,Belgium', 'Ghent,Belgium', 'Liege,Belgium',
        'Amsterdam,Netherlands', 'Eindhoven,Netherlands', 'Rotterdam,Netherlands', 'Essen,Germany',
        'Bonn,Germany', 'Cologne,Germany', 'Dortmund,Germany', 'Bremen,Germany', 'Frankfurt,Germany',
        'Hamburg,Germany', 'Hanover,Germany', 'Dresden,Germany', 'Stuttgart,Germany', 'Munich,Germany',
        'Basel,Switzerland', 'Zürich,Switzerland', 'Vienna,Austria', 'Graz,Austria', 'Milan,Italy',
        'Turin,Italy', 'Parma,Italy', 'Bologna,Italy', 'Florence,Italy', 'Rome,Italy', 'Barcelona,Spain'
    ]
    dist = 5000

    vClasses = ["passenger", "bicycle"]
    nMobiles = 100
    sTime = 0
    eTime = 12000
    
    folder = "C:\\Users\\MONSTER\\my_data2\\osm\\"

    # Create the output folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    
    for i in range(iterations):
        fname = os.path.join(folder, f"{i}_osm_bbox_{dist}")
        osmFile = fname + ".osm.xml"
        netFile = os.path.join(folder, f'{i}_osm_bbox_{dist}_osm.net.xml')  # Güncellenmiş netFile yolu
        polyFile = fname + ".poly.xml"

        print(fname)
        print(osmFile)
        print(netFile)

        # Download OSM file
        print(f"Downloading OSM file: {osmFile}")
        getMapFromOSM(places[i], dist, folder, f"{i}_osm_bbox_{dist}.osm.xml")

        # Check if the OSM file was downloaded successfully
        if not os.path.exists(osmFile):
            print(f"OSM file does not exist: {osmFile}")
            continue  # Eğer dosya yoksa, döngünün sonraki iterasyonuna geç

        # Generate net file
        generateSUMONetFromOSM(osmFile, folder, i)  # Buraya iterasyon sayısını ekledik

        # Check if the net file was generated successfully
        if not os.path.exists(netFile):
            print(f"Network file does not exist: {netFile}")
            continue  # Eğer dosya yoksa, döngünün sonraki iterasyonuna geç

        # Extract polygons from the net file
        generateRandomTrips(netFile, polyFile, vClasses[i % len(vClasses)], nMobiles, sTime, eTime)
        extractPolygonsFromOSM(osmFile, netFile, polyFile, polyFile)

        # Prepare the config file
        configFile = os.path.join(folder, f"{i}_osm_bbox_{dist}.sumo.cfg")
        generateConfigFile(netFile, polyFile, polyFile, configFile)

        # Run the simulation
        traceFile = os.path.join(folder, f"{i}_osm_bbox_{dist}.fcd.xml")
        runSimulation(configFile, traceFile)

        # Convert trace to NS2 format
        ns2File = os.path.join(folder, f"{i}_osm_bbox_{dist}.ns2mobility")
        convertTrace(traceFile, ns2File)
