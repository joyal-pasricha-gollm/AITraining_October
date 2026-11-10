import asyncio

from dotenv import load_dotenv
from agent_framework import AgentResponse
from agent_framework.orchestrations import SequentialBuilder

from agents import create_agents


load_dotenv()


async def main() -> None:
    inventory_agent, pricing_agent, recommendation_agent = create_agents()

    workflow = SequentialBuilder(
        participants=[
            inventory_agent,
            pricing_agent,
            recommendation_agent,
        ],
        output_from="all",
    ).build()

    question = input("You: ").strip()
    if not question:
        print("Please enter a request.")
        return

    result = await workflow.run(question)

    for output in result.get_outputs():
        if isinstance(output, AgentResponse):
            for message in output.messages:
                agent_name = message.author_name or "Agent"
                print(f"\n--- {agent_name} ---")
                print(message.text)


if __name__ == "__main__":
    asyncio.run(main())