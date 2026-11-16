# Travel Weather Advisory Assistant
KINDLY REFER TO THE "Console evidence Screenshots and testing.docx" file to see excuted outputs.

FastAPI service using SQLite for trips, Redis for per-session memory, Open-Meteo for live forecasts, and LangChain with a local Ollama model for travel advice.

## How an answer is produced

1. **Stage 1 – tools:** the LangChain tools `trip_lookup_tool` (SQLite) and `weather_lookup_tool` (Open-Meteo geocoding + forecast) fetch the facts.
2. **Stage 2 – LangChain chain:** `ChatPromptTemplate | ChatOllama (qwen2.5:3b) | text clean-up` writes the advice.

## Prerequisites

- Python 3.12 (Python 3.14 is not supported by the pinned packages)
- Ollama with `qwen2.5:3b`
- Redis available at `localhost:6379` (run here with Docker Desktop)

## Setup and run (Windows PowerShell)

Open two PowerShell terminals in the project folder:

1. Start Redis (first time creates the container; afterwards just start it):

   ```powershell
   docker run -d --name travel-redis -p 6379:6379 redis:7-alpine
   # later runs:
   docker start travel-redis
   ```

2. Make sure Ollama is running (Ollama desktop app) and the model is pulled. If `ollama` is not on PATH, use the full path:

   ```powershell
   & "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" pull qwen2.5:3b
   & "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe" list
   ```

3. Set up and run the API:

   ```powershell
   py -3.12 -m venv .venv312
   .\.venv312\Scripts\Activate.ps1
   pip install -r requirements.txt
   Copy-Item .env.example .env
   python init_db.py
   python -m pytest -q
   python -m uvicorn app.main:app --reload
   ```

   If `.env` already exists, keep it; do not overwrite local settings. The defaults in `.env.example` work for local services on their default ports.

4. Open `http://127.0.0.1:8000/docs` in a browser. Use Swagger UI's **Try it out** buttons to follow the evidence walkthrough below.

## Swagger evidence walkthrough

Use dates that are upcoming and within Open-Meteo's published forecast horizon for the live-weather example. The API accepts trips up to 31 days long.

1. **Save a trip**
   - Expand **POST `/trips`** and click **Try it out**.
   - Enter an employee reference, a real destination such as Jaipur, upcoming `start_date` and `end_date` values, and a purpose.
   - Click **Execute**.
   - Confirm the response is **201**. Copy its `trip_id`; you will use it in the next requests.

2. **Retrieve the saved trip**
   - Expand **GET `/trips/{trip_id}`**, click **Try it out**, enter the copied ID, and click **Execute**.
   - Confirm the response is **200** and shows the trip details.

3. **Ask for a live-weather advisory**
   - Expand **POST `/assistant/ask`**, click **Try it out**, and submit:

     ```json
     {
       "session_id": "demo_EMP104",
       "trip_id": 1,
       "question": "What weather should I expect, and what should I pack?"
     }
     ```

   - Replace `trip_id` with the ID you copied in step 1. Click **Execute**.
   - Confirm the response is **200**, `source` is `trip+live-weather`, and the answer contains `Destination:`, `Weather:`, `Packing check:`, `Answer:` and 4 `Suggestions`.

4. **Demonstrate remembered follow-up**
   - In the same **POST `/assistant/ask`** form, keep the same `session_id`, remove `trip_id`, and change the question to:

     ```json
     {
       "session_id": "demo_EMP104",
       "question": "Will I need an umbrella there?"
     }
     ```

   - Click **Execute**. Confirm it returns **200** for the same trip without requiring its ID again.
   - Session isolation: send the same question with a different `session_id` (e.g. `unrelated_session`) and no `trip_id`. Confirm **400** "Provide trip_id for the first question in a session."

5. **Show an invalid-input response**
   - Expand **POST `/trips`** and submit a trip whose `end_date` is before its `start_date`.
   - Click **Execute** and confirm the response is **422**.

6. **Show unavailable-forecast handling**
   - Create another valid trip to a real destination, but choose dates about 60 days in the future (outside the forecast horizon).
   - Copy its returned ID and ask about its weather using a new session ID.
   - Confirm the response is **200**, `source` is `trip-only`, and the answer clearly says the live forecast is unavailable and does not claim specific weather.

7. **Show unknown-destination and missing-trip handling**
   - Create a trip with a made-up destination (e.g. `Qwxzplorvilleabc`) and ask about it: **200**, `trip-only`, "Destination ... was not found".
   - Ask with `"trip_id": 999`: **404** "Trip 999 was not found."


## Sample trips

`python init_db.py` creates idempotent upcoming sample trips for EMP104 (Jaipur), EMP105 (Mumbai), and EMP106 (Bengaluru). The script avoids duplicate sample entries for the same employee and start date.

## Automated tests

```powershell
python -m pytest -q
```


