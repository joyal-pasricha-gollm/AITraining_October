import httpx
import pytest

from app import weather


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def json(self):
        return self.payload

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://weather.test")
            response = httpx.Response(self.status_code, request=request)
            raise httpx.HTTPStatusError(
                "weather API failed", request=request, response=response
            )


class FakeAsyncClient:
    def __init__(self, responses, requests):
        self.responses = iter(responses)
        self.requests = requests

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    async def get(self, url, params):
        self.requests.append((url, params))
        return next(self.responses)


def install_fake_client(monkeypatch, responses):
    requests = []
    monkeypatch.setattr(
        weather.httpx,
        "AsyncClient",
        lambda **kwargs: FakeAsyncClient(responses, requests),
    )
    return requests


@pytest.mark.asyncio
async def test_get_weather_returns_temperature_and_precipitation(monkeypatch):
    requests = install_fake_client(
        monkeypatch,
        [
            FakeResponse(
                {
                    "results": [
                        {
                            "name": "Jaipur",
                            "country": "India",
                            "latitude": 26.9,
                            "longitude": 75.8,
                        }
                    ]
                }
            ),
            FakeResponse(
                {
                    "daily": {
                        "time": ["2026-11-18"],
                        "weather_code": [61],
                        "temperature_2m_min": [18],
                        "temperature_2m_max": [27],
                        "precipitation_sum": [2.4],
                        "precipitation_probability_max": [60],
                    }
                }
            ),
        ],
    )

    result = await weather.get_weather(
        "Jaipur", weather.date(2026, 11, 18), weather.date(2026, 11, 18)
    )

    assert result["resolved_name"] == "Jaipur"
    assert result["days"][0] == {
        "date": "2026-11-18",
        "condition": "light rain",
        "min_c": 18,
        "max_c": 27,
        "precipitation_mm": 2.4,
        "precipitation_probability_pct": 60,
    }
    assert requests[1][1]["latitude"] == 26.9
    assert requests[1][1]["daily"] == (
        "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,"
        "precipitation_probability_max"
    )


@pytest.mark.asyncio
async def test_get_weather_reports_unknown_destination(monkeypatch):
    install_fake_client(monkeypatch, [FakeResponse({"results": []})])

    with pytest.raises(weather.DestinationNotFound, match="was not found"):
        await weather.get_weather(
            "Nowhereville", weather.date(2026, 11, 18), weather.date(2026, 11, 18)
        )


@pytest.mark.asyncio
async def test_get_weather_reports_unsupported_forecast_dates(monkeypatch):
    install_fake_client(
        monkeypatch,
        [
            FakeResponse(
                {
                    "results": [
                        {
                            "name": "Jaipur",
                            "latitude": 26.9,
                            "longitude": 75.8,
                        }
                    ]
                }
            ),
            FakeResponse({"reason": "Date is outside forecast range"}, status_code=400),
        ],
    )

    with pytest.raises(weather.ForecastUnavailable, match="outside forecast range"):
        await weather.get_weather(
            "Jaipur", weather.date(2026, 11, 18), weather.date(2026, 11, 18)
        )


@pytest.mark.asyncio
async def test_get_weather_reports_external_service_failure(monkeypatch):
    install_fake_client(monkeypatch, [FakeResponse({}, status_code=503)])

    with pytest.raises(weather.WeatherServiceError, match="temporarily unavailable"):
        await weather.get_weather(
            "Jaipur", weather.date(2026, 11, 18), weather.date(2026, 11, 18)
        )


@pytest.mark.asyncio
async def test_get_weather_reports_incomplete_forecast_data(monkeypatch):
    install_fake_client(
        monkeypatch,
        [
            FakeResponse(
                {
                    "results": [
                        {
                            "name": "Jaipur",
                            "latitude": 26.9,
                            "longitude": 75.8,
                        }
                    ]
                }
            ),
            FakeResponse({"daily": {"time": ["2026-11-18"]}}),
        ],
    )

    with pytest.raises(weather.WeatherServiceError, match="incomplete forecast data"):
        await weather.get_weather(
            "Jaipur", weather.date(2026, 11, 18), weather.date(2026, 11, 18)
        )
