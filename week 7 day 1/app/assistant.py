import json

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda
from langchain_ollama import ChatOllama

from app.config import get_settings
from app.memory import SessionMemory
from app.tools import trip_lookup_tool, weather_lookup_tool
from app.weather import WeatherServiceError

SYSTEM_PROMPT = """You are a concise business-travel adviser. Use only the supplied trip and live-weather facts. Never invent weather.
Reply in exactly this plain-text format and nothing else:
Answer: <one or two sentences that directly answer the current question>
Suggestions:
- <suggestion 1>
- <suggestion 2>
- <suggestion 3>
- <suggestion 4>
The "Packing decisions" were already made from the forecast. Repeat them when relevant and never contradict them.
Keep the reply under 120 words."""

HUMAN_TEMPLATE = """Saved trip facts: {trip_facts}
Weather summary: {weather_summary}
Packing decisions: {packing}
Daily forecast: {weather_facts}
Recent session conversation:
{history}
Current question: {question}

Answer the current question (not earlier ones) on the Answer line, then give exactly 4 different practical Suggestions.
Your Answer and Suggestions must agree with these packing decisions: {packing}"""


def summarise_weather(weather: dict) -> tuple[str, bool]:
    """Build the weather summary from tool data in code, so it cannot be invented."""
    days = weather.get("days") or []
    if not days:
        return "No daily forecast values were returned.", False
    conditions = list(dict.fromkeys(day["condition"] for day in days))
    lows = [day["min_c"] for day in days if day["min_c"] is not None]
    highs = [day["max_c"] for day in days if day["max_c"] is not None]
    rain_mm = sum(day["precipitation_mm"] or 0 for day in days)
    chances = [
        day["precipitation_probability_pct"]
        for day in days
        if day["precipitation_probability_pct"] is not None
    ]
    parts = [
        f"{', '.join(conditions)} from {days[0]['date']} to {days[-1]['date']}",
        f"{min(lows)}-{max(highs)}°C" if lows and highs else "temperature unavailable",
        f"total precipitation {rain_mm:.1f} mm",
    ]
    if chances:
        parts.append(f"highest rain chance {max(chances)}%")
    rain_expected = rain_mm > 0 or (max(chances) if chances else 0) >= 40
    return "; ".join(parts) + ".", rain_expected

# Stage 2 prompt: turns the facts gathered by the tools (stage 1) into an advisory.
ADVISORY_PROMPT = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_PROMPT), ("human", HUMAN_TEMPLATE)]
)


def build_advisory_chain(llm):
    """LangChain chain for stage 2: prompt -> local Ollama model -> plain text."""

    async def call_model(prompt_value):
        return await llm.ainvoke(prompt_value.to_messages())

    def to_text(message) -> str:
        content = message.content
        text = (content if isinstance(content, str) else str(content)).strip()
        start = text.find("Answer:")
        if start > 0:
            text = text[start:]
        # Tidy the layout: one Suggestions heading and up to 4 unique bullets.
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        bullets = list(dict.fromkeys(line for line in lines if line.startswith("-")))[:4]
        if not bullets:
            return text
        other = [l for l in lines if not l.startswith("-") and l.lower() != "suggestions:"]
        answer_text = " ".join(other).replace("Suggestions:", "").strip()
        if not answer_text.startswith("Answer:"):
            answer_text = f"Answer: {answer_text}"
        return "\n".join([answer_text, "Suggestions:"] + bullets)

    return ADVISORY_PROMPT | RunnableLambda(call_model) | RunnableLambda(to_text)


def _history_line(message: dict) -> str:
    """Keep only the short answer of earlier replies so the model does not copy them."""
    content = message["content"]
    if message["role"] == "assistant":
        for line in content.splitlines():
            if line.startswith("Answer:"):
                return line[len("Answer:"):].strip()
    return content[:300]


class AssistantGenerationError(RuntimeError):
    """The local model could not generate an answer."""


def _unavailable_weather_answer(trip: dict, reason: str) -> str:
    reason = reason.strip()
    if not reason.endswith("."):
        reason += "."
    return (
        f"Live weather is unavailable for {trip['destination']} from "
        f"{trip['start_date']} to {trip['end_date']}: {reason} I can't confirm "
        "the conditions. Check the forecast closer to departure. Suggestions: "
        "recheck the forecast before packing; choose layers based on the updated "
        "forecast; bring rain gear only if rain is forecast; check baggage limits "
        "and meeting attire."
    )


async def answer_question(
    session_id: str,
    question: str,
    trip_id: int | None,
    memory: SessionMemory,
) -> tuple[int, str, str]:
    resolved_trip_id = trip_id or await memory.get_trip_id(session_id)
    if not resolved_trip_id:
        raise ValueError("Provide trip_id for the first question in a session.")

    trip = json.loads(trip_lookup_tool.invoke({"trip_id": resolved_trip_id}))
    if "error" in trip:
        raise LookupError(f"Trip {resolved_trip_id} was not found.")

    await memory.set_trip_id(session_id, resolved_trip_id)
    history = await memory.get_messages(session_id)

    try:
        weather_facts = json.loads(
            await weather_lookup_tool.ainvoke(
                {
                    "destination": trip["destination"],
                    "start_date": trip["start_date"],
                    "end_date": trip["end_date"],
                }
            )
        )
    except WeatherServiceError as exc:
        answer = _unavailable_weather_answer(trip, str(exc))
        await memory.add_message(session_id, "user", question)
        await memory.add_message(session_id, "assistant", answer)
        return resolved_trip_id, answer, "trip-only"

    history_text = "\n".join(
        f'{message["role"]}: {_history_line(message)}' for message in history[-6:]
    ) or "No previous messages."
    weather_summary, rain_expected = summarise_weather(weather_facts)
    lows = [d["min_c"] for d in weather_facts.get("days", []) if d.get("min_c") is not None]
    # Packing decisions are made in code from the forecast, not by the model.
    umbrella = (
        "umbrella recommended (rain is forecast)"
        if rain_expected
        else "umbrella not needed (no meaningful rain forecast)"
    )
    if not lows:
        layer = "light jacket: temperature data unavailable"
    elif min(lows) < 18:
        layer = f"light jacket recommended (lows down to {min(lows)}°C)"
    else:
        layer = f"light jacket not needed (lows stay at {min(lows)}°C or above)"
    packing = f"{umbrella}; {layer}."
    place = ", ".join(
        part for part in (weather_facts.get("resolved_name"), weather_facts.get("country")) if part
    ) or trip["destination"]
    settings = get_settings()
    try:
        llm = ChatOllama(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
            temperature=0,
            num_predict=320,
        )
        # Stage 2: tool facts from stage 1 -> LangChain advisory chain.
        advice = await build_advisory_chain(llm).ainvoke(
            {
                "trip_facts": json.dumps(trip, default=str),
                "weather_summary": weather_summary,
                "packing": packing,
                "weather_facts": json.dumps(weather_facts["days"], default=str),
                "history": history_text,
                "question": question,
            }
        )
    except Exception as exc:
        raise AssistantGenerationError(
            "The local language model could not generate an answer."
        ) from exc

    answer = (
        f"Destination: {place}\nWeather: {weather_summary}\n"
        f"Packing check: {packing[0].upper()}{packing[1:]}\n{advice}"
    )

    await memory.add_message(session_id, "user", question)
    await memory.add_message(session_id, "assistant", answer)
    return resolved_trip_id, answer, "trip+live-weather"
