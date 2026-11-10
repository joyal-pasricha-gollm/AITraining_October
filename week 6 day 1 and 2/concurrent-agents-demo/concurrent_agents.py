
import asyncio
import json
import os
import sys
from pathlib import Path
from time import perf_counter

from dotenv import load_dotenv
from agent_framework import Agent, AgentResponse
from agent_framework.orchestrations import ConcurrentBuilder
from agent_framework.openai import OpenAIChatCompletionClient

HERE = Path(__file__).resolve().parent
load_dotenv(HERE / ".env")


def load_feedback():
    """Load the same feedback records for every agent."""
    with (HERE / "feedback.json").open(encoding="utf-8") as file:
        records = json.load(file)
    if not isinstance(records, list) or not records:
        raise ValueError("feedback.json must be a non-empty JSON list")
    return records


async def main():
    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("Missing GROQ_API_KEY. Set it in .env")

    feedback = load_feedback()
    client = OpenAIChatCompletionClient(
        model=os.getenv("GROQ_CHAT_MODEL"),
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1",
    )
    # STEP 1: Three independent agents, each with a different responsibility.
    sentiment = Agent(
        client=client,
        name="SentimentAgent",
        instructions=(
            "You analyze customer sentiment. Using ONLY the given feedback JSON, "
            "count positive (ratings 4-5), neutral (rating 3), and negative "
            "(ratings 1-2) reviews. Cite 2-3 feedback IDs as examples. "
            "Give concise results. Do not invent reviews."
        ),
    )

    issues = Agent(
        client=client,
        name="IssueAgent",
        instructions=(
            "You identify recurring customer issues. Using ONLY the given "
            "feedback JSON, list the top three complaints, referencing the "
            "feedback IDs supporting each issue. Be concise. Do not infer "
            "numbers or issues not present in the data."
        ),
    )

    improvements = Agent(
        client=client,
        name="ImprovementAgent",
        instructions=(
            "You propose practical improvements to the service. Using ONLY "
            "the supplied feedback JSON, suggest three specific actions, "
            "each tied to one or more feedback IDs. Do not assume you have "
            "seen the other agents' answers. Be concise."
        ),
    )

    # STEP 2: Fan out the SAME input to all three agents concurrently.
    workflow = ConcurrentBuilder(
        participants=[sentiment, issues, improvements]
    ).build()

    # STEP 3: Run once, collect the three independent results (fan in).
    prompt = (
        "Analyze these fictional customer feedback records. "
        "Use the assigned role's instructions.\n\n"
        + json.dumps(feedback, ensure_ascii=False, indent=2)
    )

    print(f"Analyzing {len(feedback)} customer reviews with 3 concurrent agents...\n")
    started = perf_counter()
    result = await workflow.run(prompt)

    # Default aggregation returns one AgentResponse containing the agent messages.
    for output in result.get_outputs():
        if isinstance(output, AgentResponse):
            for message in output.messages:
                print(f"\n{'=' * 56}")
                print(f"{message.author_name or 'Agent'}")
                print("=" * 56)
                print(message.text or "(No text returned)")

    print(f"\nCompleted in {perf_counter() - started:.1f} seconds")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    asyncio.run(main())
