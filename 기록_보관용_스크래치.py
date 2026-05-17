import requests
import datetime

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
lat = 37.5665
lng = 126.9780

# Use a safe range: last year's calendar dates
today = datetime.date.today()
last_year = today.year - 1
start_date = f"{last_year}-01-01"
end_date = f"{last_year}-12-31"

print(f"Fetching archive data from {start_date} to {end_date}...")
try:
    resp = requests.get(ARCHIVE_URL, params={
        "latitude": lat,
        "longitude": lng,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "temperature_2m_mean",
        "timezone": "Asia/Seoul",
    }, timeout=10)
    
    if resp.status_code != 200:
        print(f"Error HTTP {resp.status_code}: {resp.text}")
    else:
        data = resp.json()
        daily = data.get("daily", {})
        mean_temps = daily.get("temperature_2m_mean", [])
        print(f"Successfully fetched daily records: {len(mean_temps)}")
        if mean_temps:
            valid_temps = [t for t in mean_temps if t is not None]
            print(f"Valid temps count: {len(valid_temps)}")
            hdd = sum(max(18.0 - t, 0) for t in valid_temps)
            cdd = sum(max(t - 24.0, 0) for t in valid_temps)
            avg = sum(valid_temps) / len(valid_temps)
            print(f"Calculated HDD: {hdd:.1f}")
            print(f"Calculated CDD: {cdd:.1f}")
            print(f"Calculated Avg: {avg:.1f}")
            
            # Let's compute climate factor using our math
            BASE_HDD = 2500
            BASE_CDD = 200
            heating_factor = hdd / BASE_HDD
            cooling_factor = cdd / BASE_CDD
            climate_factor = 0.45 * heating_factor + 0.35 * cooling_factor + 0.20
            print(f"Resulting climate factor: {climate_factor:.3f}")
except Exception as e:
    print(f"Exception: {e}")
