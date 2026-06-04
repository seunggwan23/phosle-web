"""
위치 감지 + 기상 데이터 모듈 (weather.py)

왜 이렇게 설계했는가:
1. 브라우저 Geolocation API로 사용자 위치를 자동 감지
2. Nominatim(OpenStreetMap)으로 좌표 → 한국 주소 역지오코딩
3. Open-Meteo API로 실시간 기상 데이터 가져오기 (API 키 불필요)
4. 실제 기후 데이터로 에너지 보정 계수를 계산 → 정적 지역 팩터보다 정확

리스크 관리:
- API 호출 실패 시 기본값(서울 기준)으로 폴백
- 위치 권한 거부 시 수동 선택으로 전환
"""
import requests
import streamlit as st
from datetime import datetime

# ── Open-Meteo API 엔드포인트 (무료, API 키 불필요) ──
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"

# ── 서울 기본 좌표 (폴백용) ──
DEFAULT_LAT = 37.5665
DEFAULT_LNG = 126.9780
DEFAULT_REGION = "서울특별시"

# ── 한국 주요 도시 좌표 (수동 선택용) ──
CITY_COORDS = {
    "서울·경기": (37.5665, 126.9780),
    "강원": (37.8813, 127.7298),
    "충청": (36.6357, 127.4913),
    "전라": (35.1595, 126.8526),
    "경상": (35.1796, 129.0756),
    "제주": (33.4996, 126.5312),
}


def reverse_geocode(lat: float, lng: float) -> dict:
    """
    좌표 → 한국어 주소 변환 (Nominatim/OpenStreetMap 사용)

    Returns:
        dict: region(시/도), city(시/군/구), full_address(전체 주소)
    """
    try:
        resp = requests.get(NOMINATIM_URL, params={
            "lat": lat, "lon": lng,
            "format": "json",
            "accept-language": "ko",
            "zoom": 10,
        }, headers={"User-Agent": "EnergyCoachApp/1.0"}, timeout=5)
        data = resp.json()

        address = data.get("address", {})
        # 한국 주소 체계: state(시/도), city/county(시/군/구)
        region = address.get("state", address.get("province", ""))
        city = address.get("city", address.get("county", address.get("town", "")))
        full = data.get("display_name", "")

        return {
            "region": region,
            "city": city,
            "full_address": full,
            "success": True,
        }
    except Exception as e:
        return {
            "region": DEFAULT_REGION,
            "city": "",
            "full_address": DEFAULT_REGION,
            "success": False,
            "error": str(e),
        }


def geocode(address: str) -> dict:
    """
    주소 → 위도/경도 변환 (Nominatim/OpenStreetMap 사용)

    Returns:
        dict: lat(float), lng(float), display_name(str), success(bool)
    """
    try:
        resp = requests.get("https://nominatim.openstreetmap.org/search", params={
            "q": address,
            "format": "json",
            "accept-language": "ko",
            "limit": 1
        }, headers={"User-Agent": "EnergyCoachApp/1.0"}, timeout=5)
        data = resp.json()

        if data:
            first = data[0]
            return {
                "lat": float(first["lat"]),
                "lng": float(first["lon"]),
                "display_name": first.get("display_name", ""),
                "success": True,
            }
        else:
            return {
                "success": False,
                "error": "검색 결과가 없습니다."
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def fetch_weather(lat: float, lng: float) -> dict:
    """
    Open-Meteo API로 현재 기상 데이터 + 연간 평균 가져오기.

    Returns:
        dict: 현재 기온, 습도, 풍속, 연간 난방/냉방도일 등
    """
    try:
        # 현재 날씨 + 과거 365일 일별 데이터 (연간 평균 계산용)
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

        current = data.get("current", {})

        # 연간 일별 평균 기온으로 HDD/CDD 계산
        daily = data.get("daily", {})
        mean_temps = daily.get("temperature_2m_mean", [])

        # HDD(난방도일): 18°C 기준, 기온이 낮을수록 큰 값
        # CDD(냉방도일): 24°C 기준, 기온이 높을수록 큰 값
        hdd = sum(max(18.0 - t, 0) for t in mean_temps if t is not None)
        cdd = sum(max(t - 24.0, 0) for t in mean_temps if t is not None)

        # 연간 평균 기온
        valid_temps = [t for t in mean_temps if t is not None]
        avg_temp = sum(valid_temps) / len(valid_temps) if valid_temps else 12.5

        return {
            "success": True,
            "current_temp": current.get("temperature_2m", 20),
            "feels_like": current.get("apparent_temperature", 20),
            "humidity": current.get("relative_humidity_2m", 60),
            "wind_speed": current.get("wind_speed_10m", 5),
            "weather_code": current.get("weather_code", 0),
            "hdd": round(hdd),
            "cdd": round(cdd),
            "avg_temp": round(avg_temp, 1),
            "data_days": len(valid_temps),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "current_temp": 20, "feels_like": 20,
            "humidity": 60, "wind_speed": 5,
            "weather_code": 0,
            "hdd": 2500, "cdd": 200, "avg_temp": 12.5,
            "data_days": 0,
        }


def calc_climate_factor(weather: dict) -> float:
    """
    실제 기상 데이터로 기후 보정 계수를 계산.

    기준: 서울 평균 (HDD≈2500, CDD≈200, 연평균 12.5°C) = 1.0

    보정 로직:
    - HDD가 높으면 (추운 지역) → 난방 에너지 증가
    - CDD가 높으면 (더운 지역) → 냉방 에너지 증가
    - 풍속이 높으면 → 열 손실 증가
    """
    # 서울 기준값
    BASE_HDD = 2500
    BASE_CDD = 200

    hdd = weather.get("hdd", BASE_HDD)
    cdd = weather.get("cdd", BASE_CDD)

    # 난방 에너지 비율 (HDD 기반, 서울 대비)
    heating_factor = hdd / BASE_HDD if BASE_HDD > 0 else 1.0
    # 냉방 에너지 비율 (CDD 기반, 서울 대비)
    cooling_factor = cdd / BASE_CDD if BASE_CDD > 0 else 1.0

    # 난방이 전체 에너지의 약 45%, 냉방 35%, 기타 20%
    climate_factor = 0.45 * heating_factor + 0.35 * cooling_factor + 0.20

    # 극단값 방지 (0.7 ~ 1.5 범위)
    return max(0.7, min(1.5, climate_factor))


def weather_code_to_text(code: int) -> str:
    """WMO 기상 코드 → 한국어 텍스트"""
    mapping = {
        0: "☀️ 맑음", 1: "🌤️ 대체로 맑음", 2: "⛅ 구름 조금",
        3: "☁️ 흐림", 45: "🌫️ 안개", 48: "🌫️ 짙은 안개",
        51: "🌦️ 이슬비", 53: "🌧️ 비", 55: "🌧️ 강한 비",
        61: "🌧️ 비", 63: "🌧️ 보통 비", 65: "🌧️ 강한 비",
        71: "🌨️ 눈", 73: "🌨️ 보통 눈", 75: "❄️ 강한 눈",
        80: "🌦️ 소나기", 81: "🌧️ 소나기", 82: "⛈️ 강한 소나기",
        95: "⛈️ 뇌우", 96: "⛈️ 우박 뇌우",
    }
    return mapping.get(code, "🌤️ 보통")


def get_geolocation_js() -> str:
    """
    브라우저 Geolocation API를 호출하는 JavaScript 코드.
    Streamlit의 st.components.v1.html로 실행하여 위치를 가져옴.
    """
    return """
    <script>
    function sendLocation(lat, lng) {
        // Streamlit에 위치 데이터를 전달하기 위해 URL 파라미터 사용
        const params = new URLSearchParams(window.parent.location.search);
        params.set('lat', lat.toFixed(6));
        params.set('lng', lng.toFixed(6));
        // 세션스토리지에 저장 (Streamlit이 읽을 수 있도록)
        window.parent.sessionStorage.setItem('user_lat', lat.toFixed(6));
        window.parent.sessionStorage.setItem('user_lng', lng.toFixed(6));
    }

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(
            function(pos) {
                sendLocation(pos.coords.latitude, pos.coords.longitude);
                document.getElementById('geo-status').innerHTML =
                    '<span style="color:#50C878;">✅ 위치 감지 완료 (' +
                    pos.coords.latitude.toFixed(4) + ', ' +
                    pos.coords.longitude.toFixed(4) + ')</span>';
            },
            function(err) {
                document.getElementById('geo-status').innerHTML =
                    '<span style="color:#F87171;">❌ 위치 권한이 거부되었습니다</span>';
            },
            {enableHighAccuracy: false, timeout: 10000, maximumAge: 300000}
        );
    } else {
        document.getElementById('geo-status').innerHTML =
            '<span style="color:#F87171;">❌ 이 브라우저는 위치 감지를 지원하지 않습니다</span>';
    }
    </script>
    <div id="geo-status" style="font-size:13px;color:#6B8AB0;padding:8px 0;">
        📡 위치 감지 중...
    </div>
    """
