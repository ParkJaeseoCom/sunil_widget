import json

from teacher_widgets.core.config_store import ConfigStore
from teacher_widgets.widgets.weather import (
    build_forecast_url,
    build_air_url,
    wmo_to_text,
    pm10_grade,
    pm25_grade,
    parse_weather,
    WEATHER_TIERS,
    WeatherWidget,
)


def test_urls_contain_coords_and_fields():
    f = build_forecast_url(37.617, 126.921)
    assert "latitude=37.617" in f and "longitude=126.921" in f
    assert "temperature_2m_max" in f and "forecast_days=2" in f
    a = build_air_url(37.617, 126.921)
    assert "air-quality" in a and "pm2_5" in a


def test_wmo_mapping():
    assert "맑음" in wmo_to_text(0)
    assert "흐림" in wmo_to_text(3)
    assert "비" in wmo_to_text(63)
    assert "눈" in wmo_to_text(73)
    assert "뇌우" in wmo_to_text(95)
    assert wmo_to_text(42) == "-"


def test_pm_grades():
    assert pm10_grade(25) == "좋음"
    assert pm10_grade(50) == "보통"
    assert pm10_grade(100) == "나쁨"
    assert pm10_grade(200) == "매우나쁨"
    assert pm25_grade(10) == "좋음"
    assert pm25_grade(36) == "나쁨"
    assert pm10_grade(None) == "-"


FORECAST = {
    "current": {"temperature_2m": 26.0, "weather_code": 1},
    "daily": {
        "temperature_2m_max": [26.2, 27.2],
        "temperature_2m_min": [19.6, 20.2],
        "precipitation_probability_max": [10, 74],
        "weather_code": [1, 61],
    },
}
AIR = {"current": {"pm10": 22.8, "pm2_5": 19.4}}


def test_parse_weather():
    out = parse_weather(FORECAST, AIR)
    assert out["temp"] == 26.0 and out["code"] == 1
    assert out["today_max"] == 26.2 and out["tomorrow_min"] == 20.2
    assert out["tomorrow_rain"] == 74
    assert out["pm10"] == 22.8 and out["pm25"] == 19.4


def test_parse_weather_partial():
    out = parse_weather({}, AIR)
    assert out["temp"] is None and out["pm10"] == 22.8
    out2 = parse_weather(FORECAST, {})
    assert out2["pm10"] is None and out2["temp"] == 26.0


def test_weather_tiers():
    assert WEATHER_TIERS == [(0, "now"), (300, "two_days")]


WEATHER_CACHE = {
    "fetched_at": "2026-07-02T10:00:00",
    "weather": {"temp": 26.0, "code": 1, "today_max": 26.2, "today_min": 19.6,
                "tomorrow_max": 27.2, "tomorrow_min": 20.2, "tomorrow_rain": 74,
                "pm10": 22.8, "pm25": 19.4},
}


def make_weather_widget(qtbot, tmp_path, cache=WEATHER_CACHE):
    store = ConfigStore(tmp_path / "config.json")
    store.load()
    store.data["weather"]["_skip_initial_fetch"] = True
    if cache is not None:
        p = tmp_path / "cache" / "weather.json"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    w = WeatherWidget(store)
    qtbot.addWidget(w)
    return store, w


def test_weather_widget_renders_cache(qtbot, tmp_path):
    store, w = make_weather_widget(qtbot, tmp_path)
    text = w.body_text()
    assert "26.0" in text or "26" in text
    assert "좋음" in text or "보통" in text  # PM 배지


def test_weather_widget_two_days_tier(qtbot, tmp_path):
    store, w = make_weather_widget(qtbot, tmp_path)
    w.resize(220, 350)
    w.render_weather()
    assert "내일" in w.body_text()


def test_weather_widget_two_days_missing_tomorrow_shows_dash(qtbot, tmp_path):
    """내일 값이 None이어도 'None°'가 아니라 '-°'로 표시되어야 한다(최종 리뷰 회귀)."""
    cache = {
        "fetched_at": "2026-07-02T10:00:00",
        "weather": {"temp": 26.0, "code": 1, "today_max": 26.2, "today_min": 19.6,
                    "tomorrow_max": None, "tomorrow_min": None, "tomorrow_rain": None,
                    "pm10": 22.8, "pm25": 19.4},
    }
    store, w = make_weather_widget(qtbot, tmp_path, cache=cache)
    w.resize(220, 350)
    w.render_weather()
    text = w.body_text()
    assert "None" not in text
    assert "내일 -° / -°" in text
