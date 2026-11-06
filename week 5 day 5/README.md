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

Open `.env` and replace `replace_with_your_openai_api_key` with your provider's
API key. Keep the key private. OpenAI API keys use the default OpenAI endpoint
and `gpt-4o-mini` model.

OpenRouter keys (`sk-or-...`) are detected automatically and use the OpenRouter
API endpoint. For OpenRouter, `gpt-4o-mini` is mapped to the OpenRouter model
ID `openai/gpt-4o-mini`. To select another OpenRouter model or explicitly set
the endpoint, configure `OPENAI_BASE_URL=https://openrouter.ai/api/v1` and set
`OPENAI_MODEL` to a model ID available from OpenRouter.

If authentication fails, check the key, provider endpoint, and model, and make
sure an `OPENAI_API_KEY`, `OPENAI_BASE_URL`, or `OPENAI_MODEL` environment
variable is not overriding the `.env` setting. `.env` is loaded without
overriding existing environment variables.

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
