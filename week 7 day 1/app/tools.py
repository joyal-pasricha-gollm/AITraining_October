import json
from langchain_core.tools import tool
from app.database import get_trip
from app.weather import get_weather

@tool
def trip_lookup_tool(trip_id: int) -> str:
    """Return a saved business trip by its numeric trip ID."""
    trip=get_trip(trip_id)
    return json.dumps(trip or {"error":"Trip not found"}, default=str)

@tool
async def weather_lookup_tool(destination: str, start_date: str, end_date: str) -> str:
    """Return live forecast facts for a destination and ISO travel dates."""
    from datetime import date
    result=await get_weather(destination, date.fromisoformat(start_date), date.fromisoformat(end_date))
    return json.dumps(result)
