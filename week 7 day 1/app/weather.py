from datetime import date
import httpx
from app.config import get_settings

class WeatherServiceError(RuntimeError): pass
class DestinationNotFound(WeatherServiceError): pass
class ForecastUnavailable(WeatherServiceError): pass

WEATHER_CODES = {
    0:"clear sky",1:"mainly clear",2:"partly cloudy",3:"overcast",45:"fog",48:"rime fog",
    51:"light drizzle",53:"drizzle",55:"heavy drizzle",56:"light freezing drizzle",57:"freezing drizzle",
    61:"light rain",63:"rain",65:"heavy rain",66:"light freezing rain",67:"freezing rain",
    71:"light snow",73:"snow",75:"heavy snow",77:"snow grains",80:"rain showers",81:"rain showers",
    82:"heavy rain showers",85:"snow showers",86:"heavy snow showers",95:"thunderstorm",96:"thunderstorm with hail",99:"thunderstorm with hail"
}

async def get_weather(destination: str, start_date: date, end_date: date) -> dict:
    settings = get_settings()
    timeout = httpx.Timeout(settings.http_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            geo = await client.get(settings.open_meteo_geocoding_url,
                params={"name": destination, "count": 1, "language": "en", "format": "json"})
            geo.raise_for_status()
            results = geo.json().get("results") or []
            if not results:
                raise DestinationNotFound(f"Destination '{destination}' was not found.")
            place = results[0]
            forecast = await client.get(settings.open_meteo_forecast_url, params={
                "latitude": place["latitude"], "longitude": place["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max",
                "timezone": "auto", "start_date": start_date.isoformat(), "end_date": end_date.isoformat()
            })
            if forecast.status_code == 400:
                reason = forecast.json().get("reason", "requested dates are outside the forecast horizon")
                raise ForecastUnavailable(reason)
            forecast.raise_for_status()
            daily = forecast.json().get("daily") or {}
            if not daily.get("time"):
                raise ForecastUnavailable("No forecast is available for the requested dates.")
    except (DestinationNotFound, ForecastUnavailable):
        raise
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise WeatherServiceError("The live weather service is temporarily unavailable.") from exc

    try:
        days = []
        for i, day in enumerate(daily["time"]):
            code = daily["weather_code"][i]
            days.append(
                {
                    "date": day,
                    "condition": WEATHER_CODES.get(code, f"weather code {code}"),
                    "min_c": daily["temperature_2m_min"][i],
                    "max_c": daily["temperature_2m_max"][i],
                    "precipitation_mm": daily["precipitation_sum"][i],
                    "precipitation_probability_pct": daily[
                        "precipitation_probability_max"
                    ][i],
                }
            )
    except (IndexError, KeyError, TypeError) as exc:
        raise WeatherServiceError(
            "The live weather service returned incomplete forecast data."
        ) from exc
    return {"resolved_name": place.get("name", destination), "country": place.get("country", ""), "days": days}
