#!/usr/bin/python

import os
import osmnx as ox
import subprocess
import shutil

SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"  # Update this path to your SUMO installation

# Step 1 - Download Map from OSM
def get_map_from_osm(place, dist, out_dir, out_file):
    print(f"Downloading map for place '{place}'...")
    # Geocode
    try:
        lat, lng = ox.geocode(place)
    except Exception as e:
        print(f"Error geocoding place '{place}': {e}")
        return

    # Get the bbox
    p = lat, lng
    north, south, east, west = ox.utils_geo.bbox_from_point(p, dist)
    bbox = (west, south, east, north)
    bbox_str = ','.join(map(str, bbox))
    
    # Download the bbox
    try:
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'osmGet.py'), '--bbox=' + bbox_str, '--output-dir', out_dir], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error downloading OSM data for {place}: {e}")
        return

    # Rename the file using Python shutil for Windows compatibility
    original_file = os.path.join(out_dir, 'osm_bbox.osm.xml')
    if os.path.exists(original_file):
        try:
            shutil.move(original_file, out_file)
            print(f'Renamed {original_file} to {out_file}')
        except Exception as e:
            print(f"Error renaming file: {e}")
    else:
        print(f'Warning: {original_file} not found. Please check the download process.')

# Step 2 - Convert OSM Map to SUMO Network
def generate_sumo_net_from_osm(osm_file, out_dir, net_file, iteration):
    print(f"Generating SUMO network for OSM file '{osm_file}'...")
    try:
        # Generate the net file
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'osmBuild.py'), '--osm-file', osm_file, '--netconvert-options=--tls.ignore-internal-junction-jam', '--output-directory', out_dir], check=True)

        # Rename the net file
        original_net_file = os.path.join(out_dir, 'osm.net.xml')
        if os.path.exists(original_net_file):
            shutil.move(original_net_file, net_file)
            print(f'Renamed {original_net_file} to {net_file}')
        else:
            print(f'Warning: {original_net_file} not found. Please check the generation process.')

        # Rename the netconvert configuration file similar to net file
        original_netccfg_file = os.path.join(out_dir, 'osm.netccfg')
        renamed_netccfg_file = os.path.join(out_dir, f"{iteration}_osm_bbox_5000_osm.netccfg")
        if os.path.exists(original_netccfg_file):
            shutil.move(original_netccfg_file, renamed_netccfg_file)
            print(f'Renamed {original_netccfg_file} to {renamed_netccfg_file}')
        else:
            print(f'Warning: {original_netccfg_file} not found. Please check the generation process.')

    except subprocess.CalledProcessError as e:
        print(f"Error generating SUMO network from {osm_file}: {e}")

# Step 3 - Extract TAZ Polygons from the OSM file
def extract_taz_polygons_from_osm(osm_file, net_file, type_file, out_file):
    print(f"Extracting TAZ polygons from OSM file '{osm_file}'...")
    try:
        # Kontrol yaparak type_file'in mevcut olup olmadığını kontrol et
        if not os.path.exists(type_file):
            print(f"Warning: Type file '{type_file}' not found. Skipping TAZ extraction.")
            return
        
        subprocess.run(['polyconvert', '--net-file', net_file, '--osm-files', osm_file, '--type-file', type_file, '-o', out_file, '--type', 'taz'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error extracting TAZ polygons from {osm_file}: {e}")

# Step 4 - TAZ Extraction
def extract_taz(net_file, poly_taz_file, out_file, v_class):
    net_file = os.path.normpath(net_file)
    poly_taz_file = os.path.normpath(poly_taz_file)
    out_file = os.path.normpath(out_file)

    print(f"Extracting TAZ using net file '{net_file}' for vehicle class '{v_class}'...")
    try:
        # Kontrol yaparak v_class'in tanımlı olup olmadığını kontrol et
        if v_class not in ['passenger', 'bicycle', 'bus', 'truck']:  # Desteklenen araç sınıflarını ekleyin
            print(f"Warning: Vehicle class '{v_class}' is not recognized. Skipping TAZ extraction.")
            return
        
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'edgesInDistricts.py'), '-n', net_file, '-t', poly_taz_file, '-o', out_file, '-l', v_class, '--complete'], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error extracting TAZ: {e}")


# Step 5 - Random Trips Generation
def generate_random_trips(net_file, out_file, v_class, n_mobiles, s_time, e_time):
    print(f"Generating random trips for net file '{net_file}'...")
    try:
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'randomTrips.py'), '-n', net_file, '-b', str(s_time), '-e', str(e_time), '-o', out_file, '-p', str((e_time - s_time) / n_mobiles), '--vehicle-class', v_class, '--random', '--random-depart', '--validate'], check=True)

        # Move the side-product (of validate) route file
        side_product_file = 'routes.rou.xml'
        if os.path.exists(side_product_file):
            new_route_file = out_file[:-8] + '_routes.rou.xml'
            shutil.move(side_product_file, new_route_file)
            print(f'Renamed {side_product_file} to {new_route_file}')
    except subprocess.CalledProcessError as e:
        print(f"Error generating random trips: {e}")

# Step 6 - Random Traffic to OD-matrix
def generate_routes_od_matrix(trip_file, taz_file, out_file):
    print(f"Generating routes OD matrix for trip file '{trip_file}'...")
    try:
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'route', 'route2OD.py'), '-r', trip_file, '-a', taz_file, '-o', out_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating OD matrix routes: {e}")

# Step 7 - Importing OD-matrix
def generate_od_trips(routes_od_file, taz_file, s_time, e_time, out_file, v_class):
    print(f"Generating OD trips from routes OD file '{routes_od_file}'...")
    try:
        subprocess.run(['od2trips', '--tazrelation-files', routes_od_file, '--taz-files', taz_file, '-b', str(s_time), '-e', str(e_time), '-o', out_file, '--vtype', v_class, '--prefix', v_class[:3]], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating OD trips: {e}")

# Step 8 - Routing
def generate_routes(net_file, trip_file, out_file):
    print(f"Generating routes for net file '{net_file}'...")
    try:
        subprocess.run(['duarouter', '--net-file', net_file, '--route-files', trip_file, '--output-file', out_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating routes: {e}")

# Step 9 - Prepare the Config File
def generate_config_file(net_file, route_file, poly_file, out_file):
    print(f"Generating configuration file '{out_file}'...")
    try:
        with open(out_file, 'w') as f:
            data = [
                '<configuration>',
                '<input>',
                f'<net-file value="{net_file}"/>',
                f'<route-files value="{route_file}"/>',
                f'<additional-files value="{poly_file}"/>',
                '</input>',
                '</configuration>'
            ]
            for line in data:
                f.write(line + '\n')
        print(f"Config file {out_file} created successfully.")
    except Exception as e:
        print(f"Error writing config file {out_file}: {e}")

# Step 10 - Run the Simulation
def run_simulation(config_file, trace_file):
    print(f"Running SUMO simulation with config file '{config_file}'...")
    try:
        subprocess.run(['sumo', '-c', config_file, '--fcd-output', trace_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running SUMO simulation: {e}")

# Step 11 - Convert the Trace to NS2 Format
def convert_trace(trace_file, out_file):
    print(f"Converting trace file '{trace_file}' to NS2 format...")
    try:
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'traceExporter.py'), '--fcd-input', trace_file, '--ns2mobility-output', out_file], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error converting trace file {trace_file} to NS2 format: {e}")



# Function to check if a file exists
def check_file_exists(file_path):
    if os.path.exists(file_path):
        print(f"File exists: {file_path}")
    else:
        print(f"File does not exist: {file_path}")

if __name__ == '__main__':
    print("Starting the entire process...")
    iterations = 1
    places = ['Antwerp,Belgium', 'Bruges,Belgium', 'Brussels,Belgium', 'Ghent,Belgium', 'Liege,Belgium']
    dist = 5000

    v_classes = ["passenger", "bicycle"]
    n_mobiles = 25
    s_time = 0
    e_time = 12000
    
    folder = r"C:\Users\MONSTER\my_data2\osmTaz" 

    # Create the output folder if it doesn't exist
    os.makedirs(folder, exist_ok=True)
    print(f"Output folder '{folder}' is ready.")

    for i in range(iterations):
        print(f"Processing iteration {i+1} of {iterations}...")
        fname = os.path.join(folder, f"{i}_osm_bbox_{dist}")
        
        # Step 1: Download OSM file
        osm_file = fname + ".osm.xml"
        print(f"Step 1: Downloading OSM file for '{places[i]}'...")
        get_map_from_osm(places[i], dist, folder, osm_file)
        check_file_exists(osm_file)  # Check existence after downloading OSM

        # Step 2: Generate net file
        net_file = fname + ".net.xml"
        print(f"Step 2: Generating SUMO net file from OSM file '{osm_file}'...")
        generate_sumo_net_from_osm(osm_file, folder, net_file, i)
        check_file_exists(net_file)  # Check existence after generating SUMO net

        # Step 3: Extract polygons
        type_file = os.path.join(SUMO_HOME, "data", "typemap", "osmPolyconvert.typ.xml")
        poly_file = fname + ".poly.xml"
        print(f"Step 3: Extracting TAZ polygons from OSM file '{osm_file}'...")
        extract_taz_polygons_from_osm(osm_file, net_file, type_file, poly_file)
        check_file_exists(poly_file)  # Check existence after extracting TAZ polygons

        for vc in v_classes:
            print(f"Processing vehicle class '{vc}'...")
            
            # Step 4: TAZ extraction
            taz_file = fname + ".TAZ.xml"
            print(f"Step 4: Extracting TAZ using net file '{net_file}' for vehicle class '{vc}'...")
            extract_taz(net_file, poly_file, taz_file, vc)
            check_file_exists(taz_file)  # Check existence after TAZ extraction

            # Step 5: Generate trip file
            trip_file = fname + f"_{vc}_trips.rou.xml"
            print(f"Step 5: Generating random trips for net file '{net_file}' for vehicle class '{vc}'...")
            generate_random_trips(net_file, trip_file, vc, n_mobiles, s_time, e_time)
            check_file_exists(trip_file)  # Check existence after generating trips

            # Step 6: Generate OD matrix
            od_route_file = fname + f"_{vc}_routes.xml"
            print(f"Step 6: Generating OD matrix routes from trip file '{trip_file}'...")
            generate_routes_od_matrix(trip_file, taz_file, od_route_file)
            check_file_exists(od_route_file)  # Check existence after generating OD matrix

            # Step 7: Generate OD trips
            od_trip_file = fname + f"_{vc}_od_trips.xml"
            print(f"Step 7: Generating OD trips from OD matrix routes '{od_route_file}'...")
            generate_od_trips(od_route_file, taz_file, s_time, e_time, od_trip_file, vc)
            check_file_exists(od_trip_file)  # Check existence after generating OD trips
            
            # Step 8: Generate route file
            route_file = fname + f"_{vc}_dua.rou.xml"
            print(f"Step 8: Generating route file for net file '{net_file}' and trip file '{od_trip_file}'...")
            generate_routes(net_file, od_trip_file, route_file)
            check_file_exists(route_file)  # Check existence after generating routes

            # Step 9: Generate config file
            config_file = fname + f"_{vc}.sumocfg"
            print(f"Step 9: Generating configuration file '{config_file}'...")
            generate_config_file(net_file, route_file, poly_file, config_file)
            check_file_exists(config_file)  # Check existence after generating config

            # Step 10: Run SUMO simulation
            trace_file = fname + f"_{vc}_trace.xml"
            print(f"Step 10: Running SUMO simulation with config file '{config_file}'...")
            run_simulation(config_file, trace_file)
            check_file_exists(trace_file)  # Check existence after running simulation

            # Step 11: Convert the trace file to NS2 format
            ns2_file = fname + f"_{vc}_trace.tcl"
            print(f"Step 11: Converting trace file '{trace_file}' to NS2 format...")
            convert_trace(trace_file, ns2_file)
            check_file_exists(ns2_file)  # Check existence after converting trace

    print("Process completed successfully.")

