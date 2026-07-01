# Scraper for Weather Underground

from bs4 import BeautifulSoup as bs 
import requests
from requests.exceptions import HTTPError
import convert_metric as cv
import os
import time
import config as cfg
import time

def empty_result(station_id, scrap_time):
    return {
        "station_id": station_id,
        "time": scrap_time,
        "temp": None,
        "dew": None,
        "humidity": None,
        "wind_speed": None,
        "wind_gust": None,
        "wind_dir": None,
        "pressure": None,
        "precipitation_rate": None,
        "precipitation_accum": None,
        "uv": None,
        "solar_radiation": None
    } 

def api_timestamp():
    dt = time.gmtime()
    return (
        f"{dt.tm_year:04d}-{dt.tm_mon:02d}-{dt.tm_mday:02d}"
        f"T{dt.tm_hour:02d}:{dt.tm_min:02d}:{dt.tm_sec:02d}Z"
    )

def scrape(station_id):
    for attempt in range(cfg.max_retries): # Try as many times as configured
        try: 
            url = f'https://preview.wunderground.com/dashboard/pws/{station_id}/?data-unit="m"'

            # Get time
            scrape_time = api_timestamp()

            # Load webpage
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            # Convert to bs object
            soup = bs(r.content, "html.parser")

            # Online or offline check
            status = soup.find("pws-status").find("div", id="pws-status-text").get_text(strip=True) # Find the status
            
            print(f"Station {station_id}:")
            print(status)
            print()

            if status != "connected":
                return empty_result(station_id, scrape_time)  
            else:
                #---Data Collection---
                
                #--Air--
                air = soup.find("temp-widget-view")
                
                temp = air.get('data-temp')
                print(f"Temp: {temp}")

                dew = air.get("data-dew-point")
                print(f"Dew: {dew}")

                humd = air.get("data-humidity")
                print(f"Humidity: {humd}")

                print()

                #--Wind--
                wind = soup.find("wind-widget-view")

                wind_speed = wind.get("data-wind-speed")
                print(f"Wind Speed: {wind_speed}")

                wind_gust = wind.get("data-wind-gust")
                print(f"Wind Gust: {wind_gust}")

                wind_dir = wind.get("data-wind-dir")
                print(f"Wind Direction: {wind_dir}")
                print()
                
                #--Pressure--
                pressure = soup.find("pressure-widget-view")
                
                pressure = pressure.get("data-pressure")
                print(f"Pressure: {pressure}")
                print()

                #--Precip.--
                precip = soup.find("rain-widget-view")

                precip_rate = precip.get("data-precip-rate")
                print(f"Precipitation Rate: {precip_rate}")

                precip_accum = precip.get("data-precip-total")
                print(f"Precipitation Accumulation: {precip_accum}")
                print()

                #--UV/Solar--
                uv = soup.find("uv-widget-view")
                uv = uv.get("data-uv")

                print(f"UV: {uv}")

                solar = soup.find("solar-radiation-widget-view")

                solar = solar.get("data-solar-radiation")
                print(f"Solar Radiation: {solar}")
                print()

                # Convert into floats
                temp = cv.make_float(temp)
                dew = cv.make_float(dew)
                humd = cv.make_float(humd)
                wind_speed = cv.make_float(wind_speed)
                wind_gust = cv.make_float(wind_gust)
                wind_dir = cv.make_float(wind_dir)
                pressure = cv.make_float(pressure)
                precip_rate = cv.make_float(precip_rate)
                precip_accum = cv.make_float(precip_accum)
                uv = cv.make_float(uv)
                solar = cv.make_float(solar)

                # Convert into metric
                if air['data-unit'] != "m":
                    temp = cv.f_to_c(temp)
                    dew = cv.f_to_c(dew)

                    wind_speed = cv.mph_to_knots(wind_speed)
                    wind_gust = cv.mph_to_knots(wind_gust)
                
                # Return a dict to be turned into json later
                return {
                    "station_id": station_id,
                    "time": scrape_time,
                    "temp": temp,
                    "dew": dew,
                    "humidity": humd,
                    "wind_speed": wind_speed, #KNOTS
                    "wind_gust": wind_gust,
                    "wind_dir": wind_dir,
                    "pressure": pressure,
                    "precipitation_rate": precip_rate,
                    "precipitation_accum": precip_accum,
                    "uv": uv,
                    "solar_radiation": solar
                }
        
        
        # Error Protection and retrying
        except HTTPError as e:

            if e.response.status_code == 412:
                print("HTTP ERROR 412")

            wait_time = cfg.backoff_factor ** attempt
            print(f"[HTTP ERROR]: {e}\nRetrying in {wait_time} seconds---")
            time.sleep(wait_time)
        except Exception as e:
            print(f"Failed to get data for {station_id}. Error: {e}")
            break


api_header = {
    "x-api-key" : cfg.API_KEY
}

for station in cfg.stations:
    result = scrape(station)
    print("Sending data...")
    requests.post(cfg.URL, json=result, headers=api_header)
    print(result)
