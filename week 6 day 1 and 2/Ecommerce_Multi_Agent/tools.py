import json
from pathlib import Path

from agent_framework import tool


DATA_FILE = Path(__file__).resolve().parent / "products.json"


def _load_products() -> list[dict]:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))


def _search_products_data(query: str) -> str:
    """Search the product data by product name or category."""
    search_term = " ".join(query.casefold().split())

    if not search_term:
        return json.dumps({
            "query": query,
            "message": "Search query cannot be empty.",
            "products": [],
        })

    matches = []
    for product in _load_products():
        category = product["category"].casefold()
        category_matches = (
            search_term == category
            or search_term == category + "s"
            or (category.endswith("s") and search_term == category[:-1])
        )
        name_matches = search_term in product["name"].casefold()

        if category_matches or name_matches:
            matches.append({
                "id": product["id"],
                "name": product["name"],
                "category": product["category"],
                "price_inr": product["price_inr"],
                "stock": product["stock"],
                "rating": product["rating"],
            })

    if not matches:
        return json.dumps({
            "query": query,
            "message": "No products matched the search.",
            "products": [],
        }, ensure_ascii=False)

    return json.dumps({
        "query": query,
        "count": len(matches),
        "products": matches,
    }, ensure_ascii=False)


def _calculate_order_total_data(product_id: str, quantity: int) -> str:
    """Calculate a product total and verify requested stock."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return json.dumps({
            "ok": False,
            "error": "Quantity must be a positive whole number.",
        })

    product = next(
        (
            item for item in _load_products()
            if item["id"].casefold() == product_id.strip().casefold()
        ),
        None,
    )

    if product is None:
        return json.dumps({
            "ok": False,
            "error": f"Product ID '{product_id}' was not found.",
        }, ensure_ascii=False)

    total = product["price_inr"] * quantity
    in_stock = quantity <= product["stock"]

    return json.dumps({
        "ok": in_stock,
        "product_id": product["id"],
        "name": product["name"],
        "unit_price_inr": product["price_inr"],
        "requested_quantity": quantity,
        "total_inr": total,
        "available_stock": product["stock"],
        "message": (
            "Stock is sufficient."
            if in_stock
            else "Insufficient stock for the requested quantity."
        ),
    }, ensure_ascii=False)


def _prune_allocations(
    candidates: list[tuple[float, int, tuple[int, ...]]],
) -> list[tuple[float, int, tuple[int, ...]]]:
    candidates.sort(key=lambda candidate: (candidate[1], -candidate[0]))
    frontier = []
    best_rating = -1.0
    for candidate in candidates:
        if candidate[0] > best_rating:
            frontier.append(candidate)
            best_rating = candidate[0]
    return frontier


def _compare_product_options_data(
    category: str,
    quantity: int,
    budget_inr: int,
) -> str:
    """Find the best valid single-model and mixed-model purchase options."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
        return json.dumps({
            "ok": False,
            "error": "Quantity must be a positive whole number.",
        })
    if isinstance(budget_inr, bool) or not isinstance(budget_inr, int) or budget_inr < 0:
        return json.dumps({
            "ok": False,
            "error": "Budget must be a non-negative whole number of INR.",
        })

    search_result = json.loads(_search_products_data(category))
    products = search_result.get("products", [])
    if not products:
        return json.dumps({
            "ok": True,
            "category": category,
            "quantity": quantity,
            "budget_inr": budget_inr,
            "single_model": None,
            "mixed_models": None,
            "message": "No products matched the requested category.",
        }, ensure_ascii=False)

    # State 0 means no product selected, 1 means one distinct model,
    # and 2 means at least two distinct models.
    states: dict[tuple[int, int], list[tuple[float, int, tuple[int, ...]]]] = {
        (0, 0): [(0.0, 0, ())]
    }

    for product in products:
        next_states: dict[
            tuple[int, int],
            list[tuple[float, int, tuple[int, ...]]],
        ] = {}
        max_units = min(product["stock"], quantity)
        for (units, model_count), candidates in states.items():
            for rating_sum, total, allocation in candidates:
                for product_quantity in range(min(max_units, quantity - units) + 1):
                    new_units = units + product_quantity
                    if product_quantity == 0:
                        new_model_count = model_count
                    elif model_count == 0:
                        new_model_count = 1
                    else:
                        new_model_count = 2

                    new_total = total + product["price_inr"] * product_quantity
                    if new_total > budget_inr:
                        continue

                    key = (new_units, new_model_count)
                    next_states.setdefault(key, []).append((
                        rating_sum + product["rating"] * product_quantity,
                        new_total,
                        allocation + (product_quantity,),
                    ))

        states = {
            key: _prune_allocations(candidates)
            for key, candidates in next_states.items()
        }

    def format_option(
        candidates: list[tuple[float, int, tuple[int, ...]]] | None,
    ) -> dict | None:
        if not candidates:
            return None

        rating_sum, total, allocation = max(
            candidates,
            key=lambda candidate: (candidate[0], -candidate[1]),
        )
        selected = [
            {
                "product_id": product["id"],
                "name": product["name"],
                "quantity": product_quantity,
                "unit_price_inr": product["price_inr"],
                "line_total_inr": product["price_inr"] * product_quantity,
                "stock": product["stock"],
                "rating": product["rating"],
            }
            for product, product_quantity in zip(products, allocation)
            if product_quantity
        ]
        return {
            "products": selected,
            "total_inr": total,
            "average_rating": round(rating_sum / quantity, 2),
            "requested_quantity": quantity,
        }

    return json.dumps({
        "ok": True,
        "category": category,
        "quantity": quantity,
        "budget_inr": budget_inr,
        "ranking_rule": (
            "Highest quantity-weighted average rating, then lowest total cost."
        ),
        "single_model": format_option(states.get((quantity, 1))),
        "mixed_models": format_option(states.get((quantity, 2))),
    }, ensure_ascii=False)


@tool(approval_mode="never_require")
def search_products(query: str) -> str:
    """Find products by product name or category in the product dataset."""
    print(f"[TOOL CALLED] search_products: {query}")
    return _search_products_data(query)


@tool(approval_mode="never_require")
def calculate_order_total(product_id: str, quantity: int) -> str:
    """Calculate a product order total and check available stock."""
    print(
        f"[TOOL CALLED] calculate_order_total: "
        f"{product_id}, quantity={quantity}"
    )
    return _calculate_order_total_data(product_id, quantity)


@tool(approval_mode="never_require")
def compare_product_options(category: str, quantity: int, budget_inr: int) -> str:
    """Compare the best valid same-model and mixed-model options in a category."""
    print(
        f"[TOOL CALLED] compare_product_options: category={category}, "
        f"quantity={quantity}, budget_inr={budget_inr}"
    )
    return _compare_product_options_data(category, quantity, budget_inr)