import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def main() -> None:
    load_dotenv(Path(__file__).with_name(".env"))

    endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
    agent_name = os.getenv("FOUNDRY_AGENT_NAME", "EmployeeLeaveAgent")
    if not endpoint:
        raise SystemExit("Set FOUNDRY_PROJECT_ENDPOINT in the project's .env file.")

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(
            endpoint=endpoint,
            credential=credential,
            allow_preview=True,
        ) as project_client,
        project_client.get_openai_client(agent_name=agent_name) as agent_client,
    ):
        print(f"Connected to Foundry agent '{agent_name}'.")
        print("Enter an employee leave question.")
        print("Type 'quit' or 'exit' to stop.")

        while True:
            try:
                message = input("\nQuestion> ").strip()
            except EOFError:
                print()
                break

            if message.lower() in {"quit", "exit"}:
                break
            if not message:
                continue

            response = agent_client.responses.create(input=message)
            print(f"\n{response.output_text or ''}")


if __name__ == "__main__":
    main()
