import requests

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
lat = 37.5665
lng = 126.9780

print("Fetching data...")
try:
    resp = requests.get(OPEN_METEO_URL, params={
        "latitude": lat,
        "longitude": lng,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,apparent_temperature,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean",
        "past_days": 365,
        "forecast_days": 1,
        "timezone": "Asia/Seoul",
    }, timeout=10)
    data = resp.json()
    daily = data.get("daily", {})
    mean_temps = daily.get("temperature_2m_mean", [])
    print(f"Success: {data.get('success', 'N/A')}")
    print(f"Daily key count: {len(daily)}")
    print(f"Number of daily temps returned: {len(mean_temps)}")
    if mean_temps:
        valid_temps = [t for t in mean_temps if t is not None]
        print(f"Valid temps count: {len(valid_temps)}")
        if valid_temps:
            print(f"First 5 temps: {valid_temps[:5]}")
    else:
        print("Daily temperature array is empty or missing!")
        print(f"Keys in response: {data.keys()}")
        if "error" in data or "reason" in data:
            print(f"Error details: {data.get('reason')}")
except Exception as e:
    print(f"Exception occurred: {e}")
