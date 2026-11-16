from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from redis.exceptions import RedisError
from app.assistant import AssistantGenerationError, answer_question
from app.config import get_settings
from app.database import create_trip, get_trip, init_db
from app.memory import SessionMemory
from app.schemas import AskRequest, AskResponse, Trip, TripCreate

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    app.state.memory=SessionMemory()
    yield
    await app.state.memory.close()

settings=get_settings()
app=FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

@app.exception_handler(RedisError)
async def redis_error_handler(request: Request, exc: RedisError):
    return JSONResponse(status_code=503, content={"detail":"Session memory is unavailable. Start Redis and retry."})

@app.get("/health")
async def health(request: Request):
    redis_ok=False
    try: redis_ok=bool(await request.app.state.memory.ping())
    except RedisError: pass
    return {"api":"ok", "redis":"ok" if redis_ok else "unavailable"}

@app.post("/trips", response_model=Trip, status_code=status.HTTP_201_CREATED)
def add_trip(payload: TripCreate):
    return create_trip(payload)

@app.get("/trips/{trip_id}", response_model=Trip)
def read_trip(trip_id: int):
    trip=get_trip(trip_id)
    if not trip: raise HTTPException(404, f"Trip {trip_id} was not found.")
    return trip

@app.post("/assistant/ask", response_model=AskResponse)
async def ask(payload: AskRequest, request: Request):
    try:
        trip_id, answer, source=await answer_question(payload.session_id,payload.question,payload.trip_id,request.app.state.memory)
        return AskResponse(session_id=payload.session_id,trip_id=trip_id,answer=answer,source=source)
    except ValueError as exc: raise HTTPException(400,str(exc)) from exc
    except LookupError as exc: raise HTTPException(404,str(exc)) from exc
    except AssistantGenerationError as exc:
        raise HTTPException(503,"The local language model is unavailable. Start Ollama, verify the model, and retry.") from exc
