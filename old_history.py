from bs4 import BeautifulSoup as bs 
import requests
from requests import RequestException
from requests.exceptions import HTTPError
import convert_metric as cv
from pathlib import Path
import csv
from datetime import datetime
import config as cfg
import time

# None filled dict
def empty_result(date: str):
    return {
        "date": date,
        "max_temp": None,
        "avg_temp": None,
        "avg_dew_point": None,
    } 

# csv
def make_csv(station: str):

    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    path = data_dir / f"{station.strip()}_scraped_data.csv"

    if not path.exists():
        with path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow([
                "Date", "max_temp", "mean_temp",
                "min_temp", "avg_dew_point"
            ])
    return path

def save_data(results: dict, file):
    path = file

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            results["date"],
            results["max_temp"],
            results["mean_temp"],
            results["min_temp"],
            results["avg_dew_point"],
        ])

def scrape(base_url: str, date: str):
    for attempt in range(cfg.max_retries): # Try as many times as configured
        try: 
            url = base_url + date
            # Load webpage
            r = requests.get(url, timeout=10)
            r.raise_for_status()

            # Convert to bs object
            soup = bs(r.content, "html.parser")

            #--Station Info--
            table = soup.find("content-router-wc").find("airport-body")  
            table = table.find_all("table", class_="summary-table")

            temperature_table = table[0]
            dew_table = table[1]

            temperature_rows = temperature_table.select("tbody tr")
            if len(temperature_rows) < 3:
                raise ValueError(f"Expected 3 temperature rows, found {len(temperature_rows)}")
            dew_rows = dew_table.select("tbody tr")
            if len(dew_rows) < 1:
                raise ValueError(f"Expected 1 dew point rows, found {len(dew_rows)}")



            temp_max = temperature_rows[0].find_all("td")[1].get_text(strip=True)
            temp_avg = temperature_rows[1].find_all("td")[1].get_text(strip=True)
            temp_min = temperature_rows[2].find_all("td")[1].get_text(strip=True)

            dew_point = dew_rows[0].find_all("td")[1].get_text(strip=True)

            print(f"Max Temp: {temp_max}\nAvg Temp: {temp_avg}\nMin Temp: {temp_min}\nDew Point: {dew_point}")
            
            return {
                "date": date,
                "max_temp": temp_max, 
                "mean_temp": temp_avg, 
                "min_temp": temp_min,
                "avg_dew_point": dew_point
            } 
            

        # Error Protection and retrying
        except HTTPError as e:

            if e.response.status_code == 412:
                print("HTTP ERROR 412")

            wait_time = cfg.backoff_factor ** attempt
            print(f"[HTTP ERROR]: {e}\nRetrying in {wait_time} seconds---")
            time.sleep(wait_time)
            continue
        except Exception as e:
            print(f"Failed to get data for {date}. Error: {e}")
            return empty_result(date) # Return empty


file = make_csv("kuala-lumpur")

# go every month from 2005 to 2025
for year in range(2005, 2026):
    for month in range (1, 13):
        if year == 2026 and month >1:
            break
        print(f"{year}-{month}")
        data = scrape(base_url="https://www.wunderground.com/history/monthly/my/kuala-lumpur/WMSA/date/", date=f"{year}-{month}")
        save_data(data, file)
#a, b, c, d = scrape(url)