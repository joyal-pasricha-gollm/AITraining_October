import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIAuthenticationError
from langgraph.checkpoint.memory import InMemorySaver

from guardrails import (
    clean_output,
    is_restaurant_related,
    validate_question,
)
from tools import calculate_dining_cost, search_restaurants


LOGGER = logging.getLogger(__name__)
SYSTEM_PROMPT = (
    "You are a helpful restaurant information assistant. Only answer questions "
    "about the restaurants in the provided restaurant data, including cuisine, "
    "location, seating availability, and estimated dining costs. Use the tools "
    "for restaurant information and cost calculations. Never invent restaurant "
    "names, prices, or availability. Remember the previously discussed "
    "restaurant and guest count for relevant follow-up questions. Costs are "
    "estimates only; do not make reservations, bookings, or payments. For "
    "unrelated questions, say: 'I can only help with restaurant information "
    "and estimated dining costs.'"
)


def build_agent():
    """Create the configured chat agent with in-memory checkpoints."""
    load_dotenv(Path(__file__).with_name(".env"), override=False)
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.casefold().startswith("replace_with_"):
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Add your key to the project .env file."
        )

    is_openrouter = api_key.startswith("sk-or-")
    model_name = os.getenv("OPENAI_MODEL", "").strip()
    if not model_name:
        model_name = "openai/gpt-4o-mini" if is_openrouter else "gpt-4o-mini"
    elif is_openrouter and model_name == "gpt-4o-mini":
        model_name = "openai/gpt-4o-mini"

    model_options = {
        "model": model_name,
        "temperature": 0,
    }
    base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    if base_url:
        model_options["base_url"] = base_url
    elif is_openrouter:
        model_options["base_url"] = "https://openrouter.ai/api/v1"

    model = ChatOpenAI(**model_options)
    return create_agent(
        model=model,
        tools=[search_restaurants, calculate_dining_cost],
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )


def main() -> None:
    logging.basicConfig(level=logging.ERROR, format="%(levelname)s: %(message)s")
    try:
        agent = build_agent()
    except RuntimeError as error:
        print(f"Setup error: {error}")
        raise SystemExit(1) from error

    conversation_number = 1
    previous_message_count = 0
    has_restaurant_context = False

    print("Restaurant AI Agent")
    print("Ask about restaurants, cuisine, locations, seating, or estimated costs.")
    print("Type /new to start a fresh conversation, or exit to quit.")

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if question.casefold() == "exit":
            break
        if question.casefold() == "/new":
            conversation_number += 1
            previous_message_count = 0
            has_restaurant_context = False
            print("New conversation started.")
            continue

        validation_error = validate_question(question)
        if validation_error:
            print(validation_error)
            continue
        if not is_restaurant_related(question, has_context=has_restaurant_context):
            print("I can only help with restaurant information and estimated dining costs.")
            continue

        config = {
            "configurable": {
                "thread_id": f"restaurant-{conversation_number}",
            }
        }
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": question}]},
                config=config,
            )
        except OpenAIAuthenticationError:
            print(
                "The model provider rejected the API key (401). Check the "
                "provider, key, model, and API endpoint in .env, and make sure "
                "an environment variable is not overriding them. Do not share "
                "your key."
            )
            continue
        except Exception:
            LOGGER.exception("The restaurant agent request failed.")
            print("The request could not be completed. Check the error details above.")
            continue

        messages = result["messages"]
        new_messages = messages[previous_message_count:]
        previous_message_count = len(messages)
        has_restaurant_context = True

        for message in new_messages:
            if isinstance(message, AIMessage):
                for call in message.tool_calls:
                    print(f"[TOOL]: {call['name']}")
                    print(f"Arguments: {call['args']}")
            elif isinstance(message, ToolMessage):
                print(f"[TOOL RESULT]: {message.content}")

        answer = str(messages[-1].content)
        print(f"\nAgent: {clean_output(answer)}")


if __name__ == "__main__":
    main()
