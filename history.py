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

# Playwright
from playwright.sync_api import (sync_playwright, Error as PlaywrightError)

RAW_COLUMNS = [
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

CSV_COLUMNS = [
    "station_id",
    "date",
    "observed_at_local",
    "station_timezone",
    "temp_c",
    "dewpoint_c",
    "humidity_pct",
    "wind_direction_raw",
    "wind_from_deg",
    "wind_speed_ms",
    "wind_gust_ms",
    "pressure_hpa",
    "precip_rate_mm_h",
    "precip_accum_mm",
    "uv_index",
    "solar_w_m2",
]

DIRECTIONS = {
    "N": 0.0,
    "NNE": 22.5,
    "NE": 45.0,
    "ENE": 67.5,
    "E": 90.0,
    "ESE": 112.5,
    "SE": 135.0,
    "SSE": 157.5,
    "S": 180.0,
    "SSW": 202.5,
    "SW": 225.0,
    "WSW": 247.5,
    "W": 270.0,
    "WNW": 292.5,
    "NW": 315.0,
    "NNW": 337.5,
}

DIRECTION_NAMES = {
    "NORTH": "N",
    "EAST": "E",
    "SOUTH": "S",
    "WEST": "W",
}

def direction_to_degrees(value):
    if value is None:
        return None

    text = str(value).strip().upper()
    text = DIRECTION_NAMES.get(text, text)

    return DIRECTIONS.get(text)

# None filled dict
def empty_result(date: str):
    return {
            "station_id": station_id,
            "observed_at": scrap_time.isoformat(),
            "temp": None,
            "dewpoint": None,
            "humidity": None,
            "wind_speed": None,
            "wind_gust": None,
            "wind_dir": None,
            "pressure": None,
            "precip_rate": None,
            "precip_accum": None,
            "uv": None,
            "solar": None
        } 

# csv
def make_csv(station: str):
    data_dir = Path("data")
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir / f"{station.strip()}_scraped_data.csv"

def save_data(records: dict, path: Path, station_id):
    if not records:
        print(f"[SKIP] No records to save for {station_id}")
        return

    write_header = not path.exists() or path.stat().st_size == 0

    with path.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=CSV_COLUMNS,
        )
        if write_header:
            writer.writeheader()
        writer.writerows(
            {**record, "station_id": station_id}
            for record in records
        )
    print(f"[SAVED] {len(records)} observations to {path}")
# Extract numbers
def number(value):

    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = (
        str(value)
        .replace("\xa0", " ")
        .replace("−", "-")
        .strip()
    )

    match = re.match(r"^[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text)

    return float(match.group()) if match else None

def convert_record(record):
    observed_at_local = datetime.strptime(f"{record['date']} {record['time']}","%Y-%m-%d %I:%M %p",).isoformat()

    result = {
        "date": record["date"],
        "observed_at_local": observed_at_local,
        "station_timezone": "America/New_York",

        "temp_c": cv.f_to_c(record.get("temperature")),
        "dewpoint_c": cv.f_to_c(record.get("dew_point")),
        "humidity_pct": number(record.get("humidity")),

        "wind_direction_raw": record.get("wind_direction"),
        "wind_from_deg": direction_to_degrees(record.get("wind_direction")),
        "wind_speed_ms": cv.mph_to_ms(record.get("wind_speed")),
        "wind_gust_ms": cv.mph_to_ms(record.get("wind_gust")),

        "pressure_hpa": cv.inhg_to_hpa(record.get("pressure")),

        # Assumes the source rate represents inches per hour.
        "precip_rate_mm_h": cv.inches_to_mm(record.get("precip_rate")),
        "precip_accum_mm": cv.inches_to_mm(record.get("precip_accum")),

        "uv_index": number(record.get("uv")),
        "solar_w_m2": number(record.get("solar")),
    }

    if "station_id" in record:
        result["station_id"] = record["station_id"]

    return result

def parse_table(html, date):
    soup = bs(html, "html.parser")
    table = soup.select_one('pws-history-table[data-loaded="true"] table')

    if table is None:
        raise ValueError("Observation table not found in the downloaded HTML. ")

    records = []

    for row_number, row in enumerate(table.select("tbody tr"), start=1):
        cells = row.find_all(["td", "th"], recursive=False)

        if not cells:
            continue

        # Do not shift values into the wrong columns.
        if len(cells) != len(RAW_COLUMNS):
            raise ValueError(
                f"Row {row_number}: expected {len(RAW_COLUMNS)} cells, "
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

        for column, value in zip(RAW_COLUMNS, values):
            record[column] = value

        records.append(record)

    if not records:
        raise ValueError("Observation table found, but it has no data rows.")

    return records

def scrape(base_url: str, date: str):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context(viewport={"width": 1440, "height": 1000})
            page = context.new_page()
            for attempt in range(cfg.max_retries):
                try:
                    response = page.goto(base_url, wait_until="domcontentloaded", timeout=60_000)
                    print("Opened the page")
                    if response is not None and response.status >= 400:
                        raise ValueError(f"Page returned HTTP {response.status}")

                    print("URL after navigation:", page.url)

                    # Select the table
                    page.get_by_text("Table", exact=True).click(timeout=30_000)
                    print("Clicked Table")

                    table_selector = ('pws-history-table[data-loaded="true"] table')

                    page.locator(table_selector).wait_for(state="visible", timeout=60_000)
                    print("Table found")

                    # Wait for actual observation rows
                    page.wait_for_function(
                        """
                        () => {
                            const table = document.querySelector(
                                'pws-history-table[data-loaded="true"] table'
                            );

                            if (!table) return false;

                            return Array.from(table.querySelectorAll("tbody tr")).some(row => {
                                const cells = row.querySelectorAll("td, th");

                                return (
                                    cells.length >= 10 &&
                                    /\\d{1,2}:\\d{2}/.test(cells[0].textContent)
                                );
                            });
                        }
                        """,
                        timeout=60_000,
                    )

                    print("Observation rows loaded")
                    print("Finding records...")

                    records = parse_table(page.content(), date)
                    print("Finding records...")

                    print(f"[OK] {date}: scraped {len(records)} observations")
                    return records
                except (PlaywrightError, ValueError) as e:
                    print(
                        f"[SCRAPE ERROR] {date}, "
                        f"attempt {attempt + 1}/{cfg.max_retries}: {e}"
                    )

                    if attempt + 1 < cfg.max_retries:
                        wait_time = cfg.backoff_factor ** attempt
                        print(f"Retrying in {wait_time} seconds...")

                        # Let browser operations continue during the wait.
                        page.wait_for_timeout(wait_time * 1000)

            print(f"[FAILED] No observations collected for {date}")
            return []

        finally:
            browser.close()

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

raw_records = scrape(base_url=f"https://www.wunderground.com/dashboard/pws/KNJOCEAN178/table/2026-10-31/2026-10-31/daily", date="2026-10-31")
records = [convert_record(record) for record in raw_records]
save_data(records, make_csv("KMJOCEAN178"), "KMJOCEAN178")
if records:
    print(records[0])