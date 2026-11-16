from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import assistant, database, main, tools
from app.weather import ForecastUnavailable
from init_db import seed


class FakeSessionMemory:
    def __init__(self):
        self.trip_ids = {}
        self.messages = {}

    async def get_trip_id(self, session_id):
        return self.trip_ids.get(session_id)

    async def set_trip_id(self, session_id, trip_id):
        self.trip_ids[session_id] = trip_id

    async def get_messages(self, session_id):
        return self.messages.get(session_id, []).copy()

    async def add_message(self, session_id, role, content):
        self.messages.setdefault(session_id, []).append(
            {"role": role, "content": content}
        )

    async def ping(self):
        return True

    async def close(self):
        pass


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "trips.sqlite"
    monkeypatch.setattr(
        database, "get_settings", lambda: SimpleNamespace(database_path=str(database_path))
    )
    monkeypatch.setattr(main, "SessionMemory", FakeSessionMemory)
    with TestClient(main.app) as test_client:
        yield test_client


def create_trip(client, destination="Jaipur", start=None, end=None):
    start = start or date.today() + timedelta(days=2)
    end = end or start + timedelta(days=1)
    response = client.post(
        "/trips",
        json={
            "employee_id": "EMP900",
            "destination": destination,
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "purpose": "Workshop",
        },
    )
    return response


def test_create_and_get_trip(client):
    created = create_trip(client)
    assert created.status_code == 201
    trip_id = created.json()["trip_id"]

    fetched = client.get(f"/trips/{trip_id}")
    assert fetched.status_code == 200
    assert fetched.json()["destination"] == "Jaipur"


def test_invalid_date_order_returns_422(client):
    start = date.today() + timedelta(days=3)
    response = create_trip(
        client, start=start, end=start - timedelta(days=1)
    )
    assert response.status_code == 422


def test_assistant_uses_tools_and_remembers_follow_up(client, monkeypatch):
    created = create_trip(client)
    trip_id = created.json()["trip_id"]
    tool_calls = []
    prompts = []
    real_trip_tool = tools.trip_lookup_tool
    real_weather_tool = tools.weather_lookup_tool

    class RecordingTripTool:
        def invoke(self, arguments):
            tool_calls.append(("trip", arguments))
            return real_trip_tool.invoke(arguments)

    class RecordingWeatherTool:
        async def ainvoke(self, arguments):
            tool_calls.append(("weather", arguments))
            return await real_weather_tool.ainvoke(arguments)

    async def fake_get_weather(destination, start_date, end_date):
        return {
            "resolved_name": destination,
            "country": "India",
            "days": [
                {
                    "date": start_date.isoformat(),
                    "condition": "clear sky",
                    "min_c": 20,
                    "max_c": 30,
                    "precipitation_mm": 0,
                    "precipitation_probability_pct": 0,
                }
            ],
        }

    class FakeChatOllama:
        def __init__(self, **kwargs):
            pass

        async def ainvoke(self, messages):
            prompts.append(messages[-1].content)
            return SimpleNamespace(
                content="Jaipur will be clear. Pack light layers, sunglasses, "
                "comfortable shoes, and your meeting essentials."
            )

    monkeypatch.setattr(assistant, "trip_lookup_tool", RecordingTripTool())
    monkeypatch.setattr(assistant, "weather_lookup_tool", RecordingWeatherTool())
    monkeypatch.setattr(tools, "get_weather", fake_get_weather)
    monkeypatch.setattr(assistant, "ChatOllama", FakeChatOllama)

    first = client.post(
        "/assistant/ask",
        json={
            "session_id": "session_one",
            "trip_id": trip_id,
            "question": "What weather should I expect?",
        },
    )
    follow_up = client.post(
        "/assistant/ask",
        json={
            "session_id": "session_one",
            "question": "Will I need an umbrella there?",
        },
    )

    assert first.status_code == 200
    assert first.json()["source"] == "trip+live-weather"
    assert follow_up.status_code == 200
    assert follow_up.json()["trip_id"] == trip_id
    assert "What weather should I expect?" in prompts[1]
    assert [call[0] for call in tool_calls] == [
        "trip",
        "weather",
        "trip",
        "weather",
    ]

    other_session = client.post(
        "/assistant/ask",
        json={"session_id": "session_two", "question": "What about the weather?"},
    )
    assert other_session.status_code == 400


def test_unavailable_weather_returns_explicit_non_fabricated_answer(
    client, monkeypatch
):
    created = create_trip(client)
    trip_id = created.json()["trip_id"]

    class UnexpectedChatOllama:
        def __init__(self, **kwargs):
            pytest.fail("The model should not invent an answer without forecast data.")

    async def unavailable_weather(destination, start_date, end_date):
        raise ForecastUnavailable(
            "requested dates are outside the forecast horizon"
        )

    monkeypatch.setattr(tools, "get_weather", unavailable_weather)
    monkeypatch.setattr(assistant, "ChatOllama", UnexpectedChatOllama)

    response = client.post(
        "/assistant/ask",
        json={
            "session_id": "forecast_failure",
            "trip_id": trip_id,
            "question": "What weather should I expect?",
        },
    )

    assert response.status_code == 200
    assert response.json()["source"] == "trip-only"
    assert "Live weather is unavailable" in response.json()["answer"]
    assert "can't confirm the conditions" in response.json()["answer"]
    assert "30°C" not in response.json()["answer"]


def test_missing_trip_returns_404(client):
    response = client.get("/trips/999")
    assert response.status_code == 404


def test_seed_creates_three_sample_trips_without_duplicates(tmp_path, monkeypatch):
    database_path = tmp_path / "seed.sqlite"
    monkeypatch.setattr(
        database, "get_settings", lambda: SimpleNamespace(database_path=str(database_path))
    )

    seed()
    seed()

    with database.connection() as connection:
        rows = connection.execute(
            "SELECT employee_id, destination FROM trips ORDER BY employee_id"
        ).fetchall()
    assert [(row["employee_id"], row["destination"]) for row in rows] == [
        ("EMP104", "Jaipur"),
        ("EMP105", "Mumbai"),
        ("EMP106", "Bengaluru"),
    ]


def test_model_failure_returns_503(client, monkeypatch):
    created = create_trip(client)
    trip_id = created.json()["trip_id"]

    async def fake_get_weather(destination, start_date, end_date):
        return {"resolved_name": destination, "country": "India", "days": []}

    class FailingChatOllama:
        def __init__(self, **kwargs):
            pass

        async def ainvoke(self, messages):
            raise RuntimeError("Ollama is unavailable")

    monkeypatch.setattr(tools, "get_weather", fake_get_weather)
    monkeypatch.setattr(assistant, "ChatOllama", FailingChatOllama)

    response = client.post(
        "/assistant/ask",
        json={
            "session_id": "model_failure",
            "trip_id": trip_id,
            "question": "What weather should I expect?",
        },
    )
    assert response.status_code == 503
    assert "local language model is unavailable" in response.json()["detail"]
