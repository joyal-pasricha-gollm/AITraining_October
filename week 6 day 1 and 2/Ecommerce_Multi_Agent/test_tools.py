import json

from tools import (
    _calculate_order_total_data,
    _compare_product_options_data,
    _search_products_data,
)


def main() -> None:
    laptops = json.loads(_search_products_data("laptops"))
    assert laptops["count"] > 0
    assert all(product["category"] == "Laptop" for product in laptops["products"])

    valid_total = json.loads(_calculate_order_total_data("P101", 2))
    assert valid_total["ok"] is True
    assert valid_total["total_inr"] == 104000

    insufficient_stock = json.loads(_calculate_order_total_data("P101", 100))
    assert insufficient_stock["ok"] is False
    assert insufficient_stock["available_stock"] == 8

    invalid_quantity = json.loads(_calculate_order_total_data("P101", 0))
    assert invalid_quantity["ok"] is False

    unknown_product = json.loads(_calculate_order_total_data("P999", 1))
    assert unknown_product["ok"] is False

    no_matches = json.loads(_search_products_data("imaginary category"))
    assert no_matches["products"] == []

    options = json.loads(_compare_product_options_data("laptops", 2, 120000))
    single = options["single_model"]
    mixed = options["mixed_models"]
    assert single["products"] == [{
        "product_id": "P104",
        "name": "Atlas Work 14",
        "quantity": 2,
        "unit_price_inr": 59000,
        "line_total_inr": 118000,
        "stock": 12,
        "rating": 4.7,
    }]
    assert single["total_inr"] == 118000
    assert single["average_rating"] == 4.7
    assert sum(item["quantity"] for item in mixed["products"]) == 2
    assert len(mixed["products"]) >= 2
    assert mixed["total_inr"] <= 120000
    assert mixed["average_rating"] == 4.65
    assert {item["product_id"] for item in mixed["products"]} == {"P101", "P102"}

    unavailable = json.loads(_compare_product_options_data("laptops", 100, 120000))
    assert unavailable["single_model"] is None
    assert unavailable["mixed_models"] is None

    unknown_category = json.loads(
        _compare_product_options_data("not a category", 2, 120000)
    )
    assert unknown_category["single_model"] is None
    assert unknown_category["mixed_models"] is None

    print("All tool checks passed.")


if __name__ == "__main__":
    main()