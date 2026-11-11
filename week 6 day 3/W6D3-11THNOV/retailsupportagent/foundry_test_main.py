import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))

    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    agent_name = os.getenv("FOUNDRY_AGENT_NAME")
    if not endpoint or not agent_name:
        raise SystemExit(
            "Set FOUNDRY_PROJECT_ENDPOINT and FOUNDRY_AGENT_NAME in the project's .env file."
        )

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client(agent_name=agent_name) as agent_client,
    ):
        print(f"Ready to send feedback to Foundry agent '{agent_name}'.")
        print("Enter customer feedback to analyze.")
        print("Type 'quit' or 'exit' to stop.")

        while True:
            try:
                feedback = input("\nFeedback> ").strip()
            except EOFError:
                print()
                break

            if feedback.lower() in {"quit", "exit"}:
                break
            if not feedback:
                continue

            response = agent_client.responses.create(
                input=f"Analyze this customer feedback:\n\n{feedback}"
            )
            print(f"\n{response.output_text}")


if __name__ == "__main__":
    main()
