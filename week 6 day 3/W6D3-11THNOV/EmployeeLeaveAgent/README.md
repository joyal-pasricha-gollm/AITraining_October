# EmployeeLeaveAgent

A small Foundry-backed employee leave assistant, exposed as a FastAPI service.
FastAPI keeps each Foundry conversation ID and the recent chat messages in Redis
for one hour.

## 1. Configure the agent in Microsoft Foundry

The Foundry project and an agent named `EmployeeLeaveAgent` have already been
created. In the Foundry portal:

1. Open that project and select the `EmployeeLeaveAgent` agent.
2. Set its instructions to the following. Keep the policy in the instructions;
   this project does not use a policy file or add leave rules in Python.

   ```text
   You are EmployeeLeaveAgent, an assistant for employee leave questions.

   Answer only questions about employee leave types, annual allowances,
   eligibility, and how to apply for leave. Politely refuse unrelated questions
   and briefly say that you can help with the company's leave policy.

   Company leave policy:
   - Casual Leave: 12 days annually.
   - Sick Leave: 10 days annually.
   - Annual Leave: 18 days annually.
   - Leave applications must be submitted at least 2 days in advance, except
     sick leave.
   - All leave requests require manager approval.

   Explain the relevant leave allowance and application procedure clearly.
   Sick leave is exempt from the 2-day advance-submission rule, but still
   requires manager approval.
   A request for 5 days of casual leave is within the stated annual allowance
   only if the employee has at least 5 days remaining. Explain that manager
   approval is required and that you cannot check an employee's remaining
   balance.

   Do not claim to submit, approve, or check a leave request or balance. Do not
   invent rules about carryover, eligibility conditions, documentation, or
   approval timelines. If the policy does not provide an answer, say that the
   information is not specified and recommend checking with the manager or HR.
   Keep answers concise, neutral, and helpful.
   ```

3. Save the agent. No tools or knowledge sources are required for these
   fictional policies.
4. Open the Foundry playground and test the sample questions below before
   connecting the API.

### Foundry playground tests

- `How many casual leave days am I entitled to?`
- `Can I apply for sick leave tomorrow?`
- `What is the process for applying for annual leave?`
- `Can I take 5 days of casual leave?`
- `What is the capital of France?`

Expected behavior: state the relevant policy accurately; clarify that all
requests need manager approval; allow short-notice sick leave under the stated
exception; do not claim to know an employee's remaining balance; and refuse the
unrelated capital-of-France question.

## 2. Configure the local environment

Open this folder as a PyCharm project. Use Python 3.10 or later.

The existing `.env` file should contain these settings. Keep the real values
private and do not commit `.env`:

```dotenv
FOUNDRY_PROJECT_ENDPOINT=<your Foundry project endpoint>
FOUNDRY_AGENT_NAME=EmployeeLeaveAgent
REDIS_URL=redis://localhost:6379/0
```

Use the **project endpoint** shown in Foundry, not the Azure OpenAI model
endpoint. This integration connects through `AIProjectClient`, so an
`AZURE_OPENAI_ENDPOINT` value is not needed by these scripts.

In a PowerShell terminal, change to this project folder and create the virtual
environment. `py -3` uses the Python 3 installation selected on your machine:

```powershell
Set-Location 'C:\Users\Trainer\PycharmProjects\W6D3-11THNOV\EmployeeLeaveAgent'
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

If PowerShell prevents virtual-environment activation, use PyCharm's
**Settings > Project > Python Interpreter** to select
`.venv\Scripts\python.exe`, then run the install commands in PyCharm's terminal.

## 3. Sign in to Azure

`DefaultAzureCredential` needs an identity that can access the Foundry project.
For local development with Azure CLI:

```powershell
az login
az account show
az config set core.enable_broker_on_windows=false
```

If you have more than one subscription, select the one containing the Foundry
project:

```powershell
az account set --subscription "<subscription-id-or-name>"
```

Your signed-in identity must have permission to use the project and agent.

## 4. Start Redis in Docker

Install and start Docker Desktop first, then run:

```powershell
docker run -d --name employee-leave-redis -p 127.0.0.1:6379:6379 -v employee_leave_redis_data:/data redis:7-alpine redis-server --appendonly yes
docker exec employee-leave-redis redis-cli ping
```

The ping should return `PONG`. If the container already exists, start it
instead of creating another:

```powershell
docker start employee-leave-redis
docker exec employee-leave-redis redis-cli ping
```

## 5. Try the agent directly from PyCharm (optional)

This checks the Foundry connection without starting FastAPI or Redis:

```powershell
python foundry_test_main.py
```

Enter a leave question, then type `quit` to exit.

## 6. Run the FastAPI service

Keep Redis running. In the project folder:

```powershell
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` in a browser. Expand **POST /chat**, select
**Try it out**, and submit:

```json
{
  "message": "How many casual leave days am I entitled to?"
}
```

The response contains a `session_id` and the agent's `reply`. Copy the
`session_id`, expand **GET /history/{session_id}**, enter that ID, and execute
to view the messages saved for the session. Reuse the same ID in a later
`POST /chat` request to continue that Foundry conversation:

```json
{
  "message": "Can I take 5 days of casual leave?",
  "session_id": "paste-the-session-uuid-here"
}
```

The conversation and history expire after one hour of inactivity. Redis keys
for this app use the `employee_leave:` prefix. To inspect them:

```powershell
docker exec -it employee-leave-redis redis-cli
KEYS employee_leave:*
```

Use `exit` to leave the Redis prompt. Stop the API with `Ctrl+C`. To stop Redis:

```powershell
docker stop employee-leave-redis
```

## API summary

- `POST /chat`: send a message; optionally include a `session_id` UUID.
- `GET /history/{session_id}`: retrieve the messages saved for that session.
- Chat request message length is limited to 1–2,000 characters.

This is a local learning/demo service. Redis stores short-lived chat history;
there is no employee database, leave-balance lookup, or leave-request
submission/approval integration.
