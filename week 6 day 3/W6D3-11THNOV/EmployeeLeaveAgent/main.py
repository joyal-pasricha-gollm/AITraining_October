import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import redis
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field


load_dotenv(Path(__file__).with_name(".env"))

project_endpoint = os.getenv("FOUNDRY_PROJECT_ENDPOINT")
if not project_endpoint:
    raise RuntimeError("FOUNDRY_PROJECT_ENDPOINT must be set in the project's .env file.")

agent_name = os.getenv("FOUNDRY_AGENT_NAME", "EmployeeLeaveAgent")

app = FastAPI(title="Employee Leave Agent API")
session_ttl = 3600

db = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
)

project = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),
    allow_preview=True,
)
agent = project.get_openai_client(agent_name=agent_name)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: UUID | None = None


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    session_id = str(request.session_id or uuid4())
    conversation_key = f"employee_leave:{session_id}:conversation"
    history_key = f"employee_leave:{session_id}:history"

    conversation_id = db.get(conversation_key)
    if not conversation_id:
        conversation = agent.conversations.create()
        conversation_id = conversation.id
        db.set(conversation_key, conversation_id, ex=session_ttl)

    response = agent.responses.create(
        conversation=conversation_id,
        input=request.message,
    )
    answer = response.output_text or ""

    with db.pipeline() as pipe:
        pipe.rpush(
            history_key,
            json.dumps({"role": "user", "message": request.message}),
            json.dumps({"role": "assistant", "message": answer}),
        )
        pipe.expire(history_key, session_ttl)
        pipe.expire(conversation_key, session_ttl)
        pipe.execute()

    return {"session_id": session_id, "reply": answer}


@app.get("/history/{session_id}")
def get_history(session_id: UUID) -> dict[str, object]:
    history_key = f"employee_leave:{session_id}:history"
    messages = db.lrange(history_key, 0, -1)

    return {
        "session_id": str(session_id),
        "messages": [json.loads(message) for message in messages],
    }
