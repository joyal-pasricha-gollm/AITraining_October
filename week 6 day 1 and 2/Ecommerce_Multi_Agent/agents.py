import os

from agent_framework import Agent
from agent_framework.openai import OpenAIChatCompletionClient

from tools import compare_product_options, search_products


def create_agents():
    # api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    # if not api_key:
    #     raise RuntimeError(
    #         "Set OPENROUTER_API_KEY in .env to use OpenRouter."
    #     )
    #
    # client = OpenAIChatCompletionClient(
    #     model="openrouter/free",
    #     api_key=api_key,
    #     base_url="https://openrouter.ai/api/v1",
    # )
    client = OpenAIChatCompletionClient(
        model=os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-20b"),
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )

    inventory_agent = Agent(
        client=client,
        name="InventoryAgent",
        instructions=(
            "You are the inventory specialist for an e-commerce store. "
            "Read the customer's request and use search_products to search "
            "the product dataset by the relevant product name or category. "
            "Report only products and details returned by the tool, including "
            "product ID, price, stock, and rating. Preserve the requested "
            "quantity and budget from the customer's request for the next "
            "agent. If there are no matches, say so clearly. Do not calculate "
            "prices or invent product information."
        ),
        tools=[search_products],
    )

    pricing_agent = Agent(
        client=client,
        name="PricingAgent",
        instructions=(
            "You are the pricing and stock-validation specialist. Extract the "
            "requested product category, exact total quantity, and total "
            "budget from the customer's original request. Call "
            "compare_product_options exactly once with those values. Report "
            "both the best single-model option and best mixed-model option "
            "from the tool result, or clearly state when either is unavailable. "
            "The tool's results are authoritative for stock, totals, and "
            "ratings. Do not invent or combine options yourself. The requested "
            "quantity is the total number of units across the option."
        ),
        tools=[compare_product_options],
    )

    recommendation_agent = Agent(
        client=client,
        name="RecommendationAgent",
        instructions=(
            "You are the product recommendation specialist. Use only the "
            "verified pricing-tool results. Present the single-model option "
            "and mixed-model option separately, preserving each product ID "
            "and quantity exactly as returned. Explain that each option "
            "fulfills the requested total quantity and meets its stock and "
            "budget checks. Do not create or alter combinations, totals, "
            "ratings, or stock claims. If neither option is available, say so."
        ),
    )

    return inventory_agent, pricing_agent, recommendation_agent