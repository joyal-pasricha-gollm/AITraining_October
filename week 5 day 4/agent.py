
import os

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.messages import AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver

from tools import (
    search_workshops,
    calculate_workshop_fee,
    list_all_workshops,
    find_cheapest_workshop,
)
from guardrails import contains_pii, clean_output


# STEP 1: Load environment
load_dotenv()

# STEP 2: Create model
model = ChatOpenAI(
    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
    temperature=0
)

# STEP 3: Create agent
agent = create_agent(
    model=model,
    tools=[
        search_workshops,
        calculate_workshop_fee,
        list_all_workshops,
        find_cheapest_workshop
    ],
    system_prompt=(
    "You are a Workshop AI Assistant. "
    "Use list_all_workshops to show all workshops and find_cheapest_workshop "
    "to identify the lowest-priced workshop. When calculating a fee, use "
    "a coupon code supplied by the user if they provide one."
    ),
    checkpointer=InMemorySaver()
)
# STEP 4: Run application
if __name__ == "__main__":

    thread_number = 1
    previous_count = 0

    print("LangChain Workshop AI Agent")
    print("Type /new for a new conversation")
    print("Type exit to quit")

    while True:
        question = input("\nYou: ").strip()

        if question.lower() == "exit":
            break

        if question.lower() == "/new":
            thread_number += 1
            previous_count = 0
            print("New conversation started.")
            continue

        if not question:
            continue

        config = {
            "configurable": {
                "thread_id": f"workshop-{thread_number}"
            }
        }

        try:
            if contains_pii(question):
                print("Please remove personal contact details before continuing.")
                continue
            result = agent.invoke(
                {
                    "messages": [
                        {"role": "user", "content": question}
                    ]
                },
                config=config
            )

            messages = result["messages"]
            new_messages = messages[previous_count:]
            previous_count = len(messages)

            for message in new_messages:

                if isinstance(message, AIMessage):
                    for call in message.tool_calls:
                        print("[TOOL]:", call["name"])
                        print("Arguments:", call["args"])

                if isinstance(message, ToolMessage):
                    print("[TOOL RESULT]:", message.content)

            print("\nAgent:", clean_output(str(messages[-1].content)))

        except Exception as error:
            print("Error:", error)
