"""Fetch the latest EPA AirNow AQI around Boston and write aqi.json.

Each neighborhood gets the AQI of its nearest AirNow monitoring station.
A station's AQI is the highest of its PM2.5 and ozone AQIs (the EPA rule).
Run by GitHub Actions; needs the AIRNOW_API_KEY secret.
"""
import json
import math
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

API_KEY = os.environ["AIRNOW_API_KEY"]

# minLon, minLat, maxLon, maxLat: Boston plus a small margin
BBOX = "-71.25,42.20,-70.95,42.45"

# Approximate center of each neighborhood (latitude, longitude).
# Names must match the ESP32 sketch and the website map exactly.
NEIGHBORHOODS = {
    "Allston": (42.3539, -71.1337),
    "Brighton": (42.3464, -71.1627),
    "Back Bay": (42.3503, -71.0810),
    "Beacon Hill": (42.3588, -71.0707),
    "Charlestown": (42.3782, -71.0602),
    "Chinatown": (42.3493, -71.0625),
    "Dorchester": (42.3016, -71.0676),
    "Downtown": (42.3555, -71.0565),
    "East Boston": (42.3702, -71.0389),
    "Fenway": (42.3429, -71.1003),
    "Hyde Park": (42.2557, -71.1245),
    "Jamaica Plain": (42.3097, -71.1151),
    "Mattapan": (42.2771, -71.0914),
    "Mission Hill": (42.3330, -71.1036),
    "North End": (42.3647, -71.0542),
    "Roslindale": (42.2832, -71.1270),
    "Roxbury": (42.3152, -71.0914),
    "South Boston": (42.3381, -71.0476),
    "South End": (42.3388, -71.0765),
    "West Roxbury": (42.2793, -71.1627),
}


def fetch_rows():
    now = datetime.now(timezone.utc)
    params = {
        "startDate": (now - timedelta(hours=3)).strftime("%Y-%m-%dT%H"),
        "endDate": now.strftime("%Y-%m-%dT%H"),
        "parameters": "PM25,OZONE",
        "BBOX": BBOX,
        "dataType": "A",
        "format": "application/json",
        "verbose": "1",
        "monitorType": "0",
        "includerawconcentrations": "0",
        "API_KEY": API_KEY,
    }
    url = "https://www.airnowapi.org/aq/data/?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.load(response)


def build_stations(rows):
    """Return {site name: {lat, lon, aqi}} using each site's latest readings."""
    latest = {}
    for row in rows:
        aqi = row.get("AQI")
        if aqi is None or aqi < 0:
            continue
        site = row.get("SiteName") or f'{row["Latitude"]},{row["Longitude"]}'
        key = (site, row["Parameter"])
        if key not in latest or row["UTC"] > latest[key][0]:
            latest[key] = (row["UTC"], aqi, row["Latitude"], row["Longitude"])

    stations = {}
    for (site, _parameter), (_utc, aqi, lat, lon) in latest.items():
        station = stations.setdefault(site, {"lat": lat, "lon": lon, "aqi": 0})
        station["aqi"] = max(station["aqi"], aqi)
    return stations


def distance_km(lat1, lon1, lat2, lon2):
    x = math.radians(lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2))
    y = math.radians(lat2 - lat1)
    return 6371 * math.hypot(x, y)


def main():
    stations = build_stations(fetch_rows())
    if not stations:
        print("No station data returned; keeping the old aqi.json")
        return

    aqi_by_name = {}
    station_by_name = {}
    for name, (lat, lon) in NEIGHBORHOODS.items():
        nearest = min(
            stations,
            key=lambda s: distance_km(lat, lon, stations[s]["lat"], stations[s]["lon"]),
        )
        aqi_by_name[name] = stations[nearest]["aqi"]
        station_by_name[name] = nearest

    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "source": "EPA AirNow",
        "neighborhoods": aqi_by_name,
        "stations": station_by_name,
    }
    with open("aqi.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"Wrote aqi.json from {len(stations)} stations")


if __name__ == "__main__":
    main()
