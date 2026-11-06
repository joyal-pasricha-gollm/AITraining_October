import json
from pathlib import Path
from typing import TypedDict

from langchain.tools import tool


RESTAURANTS_FILE = Path(__file__).with_name("restaurants.json")
MAX_GUESTS = 20


class Restaurant(TypedDict):
    id: str
    name: str
    cuisine: str
    location: str
    price_per_person: int
    available_seats: int


def get_restaurants() -> list[Restaurant]:
    """Load and validate restaurant records from the local JSON file."""
    with RESTAURANTS_FILE.open(encoding="utf-8") as restaurant_file:
        data = json.load(restaurant_file)

    if not isinstance(data, list):
        raise ValueError("restaurants.json must contain a JSON array.")

    required_fields = set(Restaurant.__annotations__)
    for index, restaurant in enumerate(data):
        if not isinstance(restaurant, dict) or not required_fields.issubset(restaurant):
            raise ValueError(f"Restaurant record {index + 1} is missing required fields.")
        if (
            not isinstance(restaurant["price_per_person"], int)
            or not isinstance(restaurant["available_seats"], int)
        ):
            raise ValueError(f"Restaurant record {index + 1} has invalid numeric fields.")

    return data


@tool
def search_restaurants(keyword: str) -> str:
    """Search the restaurant data by cuisine, restaurant name, or location."""
    search_term = keyword.strip().casefold()
    if not search_term:
        return "Enter a cuisine, restaurant name, or location to search."

    matches = [
        restaurant
        for restaurant in get_restaurants()
        if any(
            search_term in restaurant[field].casefold()
            for field in ("name", "cuisine", "location")
        )
    ]
    if not matches:
        return f"No restaurants matched '{keyword.strip()}'."
    return json.dumps(matches, ensure_ascii=False)


@tool
def calculate_dining_cost(restaurant_id: str, guests: int) -> str:
    """Estimate dining cost for a restaurant ID and 1 to 20 guests."""
    if guests < 1 or guests > MAX_GUESTS:
        return f"Guest count must be between 1 and {MAX_GUESTS}."

    restaurant = next(
        (
            item
            for item in get_restaurants()
            if item["id"].casefold() == restaurant_id.strip().casefold()
        ),
        None,
    )
    if restaurant is None:
        return f"Restaurant '{restaurant_id.strip()}' was not found."

    total = restaurant["price_per_person"] * guests
    return json.dumps(
        {
            "restaurant_id": restaurant["id"],
            "restaurant": restaurant["name"],
            "guests": guests,
            "price_per_person": restaurant["price_per_person"],
            "estimated_total": total,
            "available_seats": restaurant["available_seats"],
            "note": "Estimate only; this does not create a reservation.",
        },
        ensure_ascii=False,
    )
