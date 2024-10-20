#!/usr/bin/python

import subprocess
import os
import logging
import osmnx as ox

# Loglama ayarları
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# SUMO_HOME pathini doğru ayarla
SUMO_HOME = r"C:\Program Files (x86)\Eclipse\Sumo"

# Step 1 - OSM Verilerini İndirme
def getMapFromOSM(place, dist, outDir, outFile):
    try:
        # Geocode
        lat, lng = ox.geocode(place)
        p = lat, lng

        # Get the bbox
        north, south, east, west = ox.utils_geo.bbox_from_point(p, dist)
        bbox = west, south, east, north
        bboxStr = ','.join(map(str, bbox))
        
        # Download the bbox
        subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'osmGet.py'), '--bbox=' + bboxStr, '--output-dir', outDir])

        # Rename the file
        os.rename(os.path.join(outDir, 'osm_bbox.osm.xml'), outFile)
        logging.info("OSM verileri başarıyla indirildi: %s", outFile)

    except Exception as e:
        logging.error("OSM verileri indirme hatası: %s", str(e))

# Step 2 - OSM dosyasını SUMO Ağına Dönüştürme
def convertOSMToSUMONet(osmFile, netFile):
    try:
        logging.info("OSM dosyasını SUMO ağına dönüştürüyor: %s", osmFile)
        result = subprocess.run(['netconvert', '--osm-files', osmFile, '-o', netFile], check=True)
        if result.returncode == 0:
            logging.info("Başarıyla dönüştürüldü: %s", netFile)
        else:
            logging.error("Dönüştürme işlemi başarısız oldu. Hata kodu: %s", result.returncode)

    except Exception as e:
        logging.error("SUMO ağına dönüştürme hatası: %s", str(e))

# Step 2 - Rasgele Trafik Tripleri Üretme
def generateRandomTrips(netFile, outFile, vClass, nMobiles, sTime, eTime):
    try:
        logging.info(f"Rasgele tripler oluşturuluyor: {outFile}")
        result = subprocess.run(
            ['python', os.path.join(SUMO_HOME, 'tools', 'randomTrips.py'), '-n', netFile, '-b', str(sTime), '-e', str(eTime), '-o', outFile, 
             '-p', str((eTime - sTime) / nMobiles), '--vehicle-class', vClass, '--random', '--random-depart', '--validate'],
            check=True, capture_output=True, text=True
        )
        
        if os.path.exists(outFile):
            logging.info(f"Trip dosyası başarıyla oluşturuldu: {outFile}")
        else:
            logging.error(f"Trip dosyası oluşturulamadı: {outFile}")
            logging.error(f"randomTrips stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"randomTrips komutunda hata: {e.stderr}")
    except Exception as e:
        logging.error(f"Rasgele trip oluşturulurken hata: {str(e)}")

# Step 3 - Trafik Yönlendirme
def generateRoutes(netFile, tripFile, outFile):
    try:
        logging.info(f"Yönlendirme dosyası oluşturuluyor: {outFile}")
        result = subprocess.run(['duarouter', '--net-file', netFile, '--route-files', tripFile, '--output-file', outFile], check=True, capture_output=True, text=True)
        
        if os.path.exists(outFile):
            logging.info(f"Rota dosyası başarıyla oluşturuldu: {outFile}")
        else:
            logging.error(f"Rota dosyası oluşturulamadı: {outFile}")
            logging.error(f"duarouter stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"duarouter komutunda hata: {e.stderr}")
    except Exception as e:
        logging.error(f"Rota dosyası oluşturulurken hata: {str(e)}")

# Step 4 - SUMO Konfigürasyon Dosyasını Hazırlama
def generateConfigFile(netFile, routeFile, outFile):
    try:
        logging.info(f"Konfigürasyon dosyası oluşturuluyor: {outFile}")
        with open(outFile, 'w') as f:
            data = [
                '<configuration>', 
                '<input>',
                f'<net-file value="{netFile}"/>',
                f'<route-files value="{routeFile}"/>',
                '</input>',
                '</configuration>'
            ]
            f.write('\n'.join(data) + '\n')
        logging.info(f"Konfigürasyon dosyası başarıyla oluşturuldu: {outFile}")
    except Exception as e:
        logging.error(f"Konfigürasyon dosyası oluşturulurken hata: {str(e)}")

# Step 5 - Simülasyonu Çalıştırma
def runSimulation(configFile, traceFile):
    try:
        logging.info(f"Simülasyon başlatılıyor: {configFile}")
        result = subprocess.run(['sumo', '-c', configFile, '--fcd-output', traceFile], check=True, capture_output=True, text=True)
        
        if os.path.exists(traceFile):
            logging.info(f"Simülasyon başarıyla tamamlandı: {traceFile}")
        else:
            logging.error(f"Simülasyon verisi oluşturulamadı: {traceFile}")
            logging.error(f"sumo stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"sumo komutunda hata: {e.stderr}")
    except Exception as e:
        logging.error(f"Simülasyon çalıştırılırken hata: {str(e)}")

# Step 6 - İzleme Verisini NS2 Formatına Dönüştürme
def convertTrace(traceFile, outFile):
    try:
        logging.info(f"İzleme verisi NS2 formatına dönüştürülüyor: {outFile}")
        result = subprocess.run(['python', os.path.join(SUMO_HOME, 'tools', 'traceExporter.py'), '--fcd-input', traceFile, '--ns2mobility-output', outFile], check=True, capture_output=True, text=True)
        
        if os.path.exists(outFile):
            logging.info(f"NS2 dosyası başarıyla oluşturuldu: {outFile}")
        else:
            logging.error(f"NS2 dosyası oluşturulamadı: {outFile}")
            logging.error(f"traceExporter stderr: {result.stderr}")
    except subprocess.CalledProcessError as e:
        logging.error(f"traceExporter komutunda hata: {e.stderr}")
    except Exception as e:
        logging.error(f"İzleme verisi dönüştürülürken hata: {str(e)}")

if __name__ == '__main__':
    # Bursa ilçeleri
    districts = [
        "Osmangazi, Bursa, Türkiye",
        "Yildirim, Bursa, Türkiye",
        "Nilufer, Bursa, Türkiye",
        "Gursu, Bursa, Türkiye",
        "Kestel, Bursa, Türkiye",
        "Mudanya, Bursa, Türkiye",
        "Gemlik, Bursa, Türkiye",
        "Orhangazi, Bursa, Türkiye",
        "Buyukorhan, Bursa, Türkiye",
        "Harmancik, Bursa, Türkiye",
        "Inegol, Bursa, Türkiye",
        "Mustafakemalpasa, Bursa, Türkiye",
        "Orhaneli, Bursa, Türkiye",
        "Karacabey, Bursa, Türkiye",
        "YeniSehir, Bursa, Türkiye"
    ]

    dist = 1000  # Mesafe (metre cinsinden, örneğin 1000 m)
    outDir = r"C:\Users\MONSTER\Documents\GitHub\SUMOScripts\SUMO-1\my_data2\osm"  # Çıkış dizini

    # OSM verilerini indir ve SUMO ağına dönüştür
    for district in districts:
        osmFile = os.path.join(outDir, f"{district.split(',')[0]}.osm.xml")  # Her ilçeye ait OSM dosyası
        getMapFromOSM(district, dist, outDir, osmFile)

        # SUMO ağı için gerekli dosya yolları
        netFile = os.path.join(outDir, f"{district.split(',')[0]}.net.xml")  # Dönüştürülen SUMO ağı dosyası

        # OSM'den SUMO ağına dönüştür
        convertOSMToSUMONet(osmFile, netFile)

        # Random trips üret
        tripFile = os.path.join(outDir, f"{district.split(',')[0]}_trips.xml")
        generateRandomTrips(netFile, tripFile, vClass="passenger", nMobiles=100, sTime=0, eTime=3600)

        # Yönlendirme dosyasını oluştur
        routeFile = os.path.join(outDir, f"{district.split(',')[0]}_routes.xml")
        generateRoutes(netFile, tripFile, routeFile)

        # Konfigürasyon dosyasını oluştur
        configFile = os.path.join(outDir, f"{district.split(',')[0]}_config.sumocfg")
        generateConfigFile(netFile, routeFile, configFile)

        # Simülasyonu çalıştır
        traceFile = os.path.join(outDir, f"{district.split(',')[0]}_trace.xml")
        runSimulation(configFile, traceFile)

        # İzleme verisini dönüştür
        ns2File = os.path.join(outDir, f"{district.split(',')[0]}_trace.ns2")
        convertTrace(traceFile, ns2File)

    logging.info("Tüm ilçelerin OSM verileri başarıyla indirildi ve SUMO ağına dönüştürüldü.")
