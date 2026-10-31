from bs4 import BeautifulSoup as bs 
import re
import requests
from requests import RequestException
from requests.exceptions import HTTPError
import convert_metric as cv
from pathlib import Path
import csv
from datetime import datetime, timedelta
import pytz
import config as cfg
import time

COLUMNS = [
    "time",
    "temperature",
    "dew_point",
    "humidity",
    "wind_direction",
    "wind_speed",
    "wind_gust",
    "pressure",
    "precip_rate",
    "precip_accum",
    "uv",
    "solar",
]

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

def save_data(records: dict, file, station_id):
    path = file

    for record in records:
        record["station_id"] = station_id

    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer = csv.DictWriter(
            file,
            fieldnames=["station_id", "date"] + COLUMNS,
        )
        writer.writeheader()
        writer.writerows(records)

def parse_table(html, date):
    soup = bs(html, "html.parser")
    table = soup.select_one("table.history-table.desktop-table")

    if table is None:
        raise ValueError("Observation table not found in the downloaded HTML. "
        "The page may require JavaScript to load its data."
        )

    records = []

    for row_number, row in enumerate(table.select("tbody tr"), start=1):
        cells = row.find_all("td", recursive=False)

        if not cells:
            continue

        # Do not shift values into the wrong columns.
        if len(cells) != len(COLUMNS):
            raise ValueError(
                f"Row {row_number}: expected {len(COLUMNS)} cells, "
                f"found {len(cells)}"
            )

        values = []

        for cell in cells:
            # measurement widget, excluding its unit label.
            value_tag = cell.select_one(".wu-value")

            if value_tag is not None:
                value = value_tag.get_text(strip=True)
            else:
                value = cell.get_text(" ", strip=True)

            value = " ".join(value.replace("\xa0", " ").split())

            # Solar can contain only a unit label with no reading.
            if value.lower() in {
                "", "--", "—", "n/a", "na", "nan",
                "w/m²", "w/m2", "w/m^2",
            }:
                value = None

            values.append(value)

        record = {"date": date}

        for column, value in zip(COLUMNS, values):
            record[column] = value

        records.append(record)

    if not records:
        raise ValueError("Observation table found, but it has no data rows.")

    return records

def scrape(base_url: str, date: str):
    for attempt in range(cfg.max_retries): # Try as many times as configured
        try: 
            response = requests.get(base_url, timeout=20)
            response.raise_for_status()
            records = parse_table(response.content, date)
            print(f"[OK] {date}: scraped {len(records)} observations")
            return records
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

start_date = datetime(2025, 1, 1, 0)
end_date = datetime(2026, 10, 31, 23)
current_date = start_date

for station in cfg.stations:
    file = make_csv(station)
    # go every day from 202 to 2026
    while current_date <= end_date:
        date = f"{current_date.year}-{current_date.month}-{current_date.day}"
        #print(date)
        current_date += timedelta(days=1)
        #data = scrape(base_url=f"https://{cfg.wu_base_url}/{station}/table/{date}/{date}/daily", date)
        #save_data(data, file)

data= scrape(base_url=f"https://www.wunderground.com/dashboard/pws/KNJOCEAN178/table/2026-10-31/2026-10-31/daily", date="2026-10-31")