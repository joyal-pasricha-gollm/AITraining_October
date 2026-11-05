
import json
from pathlib import Path
from langchain.tools import tool

FILE = Path(__file__).parent / "workshops.json"
COUPON_FILE = Path(__file__).parent / "coupons.json"


def get_coupons():
    return json.loads(COUPON_FILE.read_text(encoding="utf-8"))

def get_workshops():
    return json.loads(FILE.read_text(encoding="utf-8"))


@tool
def search_workshops(keyword: str) -> str:
    """Search available workshops by title."""

    matches = [
        w for w in get_workshops()
        if keyword.lower() in w["title"].lower()
    ]

    return json.dumps(matches)


# @tool
# def calculate_workshop_fee(
#     workshop_id: str,
#     participants: int
# ) -> str:
#     """Calculate the total fee for a workshop and participant count."""
#     if participants < 1 or participants > 30:
#         return "Participant count must be between 1 and 30."

#     for workshop in get_workshops():

#         if workshop["id"] == workshop_id:
#             total = workshop["fee"] * participants

#             return json.dumps({
#                 "workshop": workshop["title"],
#                 "participants": participants,
#                 "total_fee": total
#             })

#     return "Workshop not found."

@tool
def calculate_workshop_fee(
    workshop_id: str,
    participants: int,
    coupon_code: str = ""
) -> str:
    """Calculate the workshop fee. Apply a valid coupon code if provided."""
    if participants < 1 or participants > 30:
        return "Participant count must be between 1 and 30."

    for workshop in get_workshops():
        if workshop["id"] == workshop_id:
            subtotal = workshop["fee"] * participants
            discount_percent = 0

            if coupon_code.strip():
                coupon = next(
                    (
                        item for item in get_coupons()
                        if item["code"].casefold() == coupon_code.strip().casefold()
                    ),
                    None
                )
                if coupon is None:
                    return "Invalid coupon code."

                discount_percent = coupon["discount_percent"]

            discount = round(subtotal * discount_percent / 100, 2)
            total = round(subtotal - discount, 2)

            return json.dumps({
                "workshop": workshop["title"],
                "participants": participants,
                "subtotal": subtotal,
                "coupon_code": coupon_code.strip() or None,
                "discount_percent": discount_percent,
                "discount_amount": discount,
                "total_fee": total
            })

    return "Workshop not found."

    
@tool
def list_all_workshops() -> str:
    """List all available workshops and their details."""
    return json.dumps(get_workshops())


@tool
def find_cheapest_workshop() -> str:
    """Find the available workshop with the lowest fee."""
    workshops = get_workshops()

    if not workshops:
        return "No workshops are currently available."

    cheapest = min(workshops, key=lambda workshop: workshop["fee"])
    return json.dumps(cheapest)

if __name__ == "__main__":
    print(search_workshops.invoke({"keyword": "Python"}))

    print(calculate_workshop_fee.invoke({
        "workshop_id": "W101",
        "participants": 4
    }))
