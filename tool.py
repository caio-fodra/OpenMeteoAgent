import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10


def _parse_and_validate_request(lat: Any, lon: Any, days_ahead: Any) -> tuple[float, float, int]:
    """Parse inputs into (lat, lon, days_ahead) and validate ranges."""
    try:
        parsed_lat = float(lat)
        parsed_lon = float(lon)
        parsed_days = int(days_ahead)
    except (TypeError, ValueError) as exc:
        raise ValueError("Latitude, longitude ou days_ahead inválidos.") from exc

    if not -90 <= parsed_lat <= 90:
        raise ValueError("Latitude deve estar entre -90 e 90.")
    if not -180 <= parsed_lon <= 180:
        raise ValueError("Longitude deve estar entre -180 e 180.")
    if not 1 <= parsed_days <= 16:
        raise ValueError("days_ahead deve estar entre 1 e 16.")

    return parsed_lat, parsed_lon, parsed_days


def _value_or_none(values: list[Any], index: int) -> Any | None:
    try:
        return values[index]
    except IndexError:
        return None


def get_daily_forecast(lat: float, lon: float, days_ahead: int) -> dict[str, Any]:
    lat, lon, days_ahead = _parse_and_validate_request(lat, lon, days_ahead)

    logger.info("Consultando Open-Meteo: lat=%s lon=%s days_ahead=%s", lat, lon, days_ahead)

    try:
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "forecast_days": days_ahead,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.exception("Erro HTTP ao consultar o Open-Meteo: %s", exc)
        raise RuntimeError("Falha ao consultar a API do Open-Meteo.") from exc
    except ValueError as exc:
        logger.exception("Resposta JSON inválida do Open-Meteo: %s", exc)
        raise RuntimeError("A API do Open-Meteo retornou uma resposta inválida.") from exc

    daily = data.get("daily") or {}
    dates = daily.get("time") or []
    if not dates:
        raise ValueError("A API não retornou dados diários.")

    temp_max = daily.get("temperature_2m_max") or []
    temp_min = daily.get("temperature_2m_min") or []
    precipitation = daily.get("precipitation_sum") or []
    units = data.get("daily_units") or {}

    daily_rows = [
        {
            "date": date,
            "temperature_2m_max": _value_or_none(temp_max, index),
            "temperature_2m_min": _value_or_none(temp_min, index),
            "precipitation_sum": _value_or_none(precipitation, index),
        }
        for index, date in enumerate(dates)
    ]

    return {
        "latitude": data.get("latitude", lat),
        "longitude": data.get("longitude", lon),
        "daily_units": {
            "temperature_2m_max": units.get("temperature_2m_max", "°C"),
            "temperature_2m_min": units.get("temperature_2m_min", "°C"),
            "precipitation_sum": units.get("precipitation_sum", "mm"),
        },
        "daily": daily_rows,
    }
