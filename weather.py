import json
import sys
from urllib.parse import urlencode
from urllib.request import urlopen


def get_json(url, params):
    query = urlencode(params)
    with urlopen(f"{url}?{query}", timeout=30) as response:
        return json.load(response)


def current_weather(location):
    places = get_json(
        "https://geocoding-api.open-meteo.com/v1/search",
        {"name": location, "count": 1, "language": "en", "format": "json"},
    ).get("results", [])
    if not places:
        raise ValueError(f"Location not found: {location}")

    place = places[0]
    weather = get_json(
        "https://api.open-meteo.com/v1/forecast",
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m",
            "temperature_unit": "celsius",
            "wind_speed_unit": "kmh",
        },
    )
    current = weather["current"]
    units = weather["current_units"]
    print(f"{place['name']}, {place.get('country', '')}")
    print(f"Temperature: {current['temperature_2m']} {units['temperature_2m']}")
    print(f"Humidity: {current['relative_humidity_2m']} {units['relative_humidity_2m']}")
    print(f"Wind: {current['wind_speed_10m']} {units['wind_speed_10m']}")
    print(f"Observed: {current['time']}")


if __name__ == "__main__":
    location = " ".join(sys.argv[1:]).strip()
    if not location:
        raise SystemExit("Usage: python weather.py CITY_OR_TOWN")
    try:
        current_weather(location)
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit(f"Weather lookup failed: {error}")