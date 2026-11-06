# Restaurant AI Agent

A command-line restaurant assistant built with LangChain, the supplied
`restaurants.json` data, two tools, in-memory conversation memory, and basic
guardrails. It provides restaurant information and estimated dining costs only;
it does not make reservations or take payments.

## 1. Set up the environment (Windows PowerShell)

From this folder, create and activate a virtual environment and install the
dependencies:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Open `.env` and replace `replace_with_your_openai_api_key` with your OpenAI API
key. Keep the key private. `OPENAI_MODEL` defaults to `gpt-4o-mini`.
Use an API key from the OpenAI API platform; ChatGPT subscriptions and keys
from other providers do not authenticate with the default OpenAI endpoint.
If the agent reports a 401 authentication error, create/check an active OpenAI
API key and make sure a `OPENAI_API_KEY` environment variable is not overriding
the `.env` value (`.env` is loaded without overriding existing environment
variables).

## 2. Run the agent

```powershell
python agent.py
```

The agent prints the selected tool and its arguments, then prints the tool
result and the assistant response. Type `/new` to start a conversation with
fresh memory, or `exit` to quit. Memory is held in process and is not saved
after the application exits.

## 3. Try the exercise scenarios

```text
Show me Indian restaurants.
What is the estimated cost for 4 people at Spice Garden?
Make that 6 people.
Show me Italian restaurants.
Calculate the cost for 50 guests.
What is the largest mammal?
My email is john@example.com.
/new
```

The supplied dataset includes 240 restaurants across multiple locations and
cuisines. The tools search that file and calculate `price_per_person * guests`;
guest counts must be between 1 and 20. PII is blocked on input and redacted in
displayed responses.

## 4. Run offline checks

These tests exercise the data-backed tools and guardrails without calling the
OpenAI API:

```powershell
python -m unittest -v
```
