import hashlib
import hmac
import json

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.idempotency_record import IdempotencyRecord
from app.models.user import User


def request_fingerprint(data: dict) -> str:
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hmac.new(
        settings.jwt_secret_key.encode("utf-8"),
        canonical.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def replay_if_present(
    db: Session, actor: User, operation: str, key: str, fingerprint: str
) -> IdempotencyRecord | None:
    record = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.actor_id == actor.id,
            IdempotencyRecord.operation == operation,
            IdempotencyRecord.key == key,
        )
    )
    if record is None:
        return None
    if record.request_hash != fingerprint:
        raise HTTPException(
            409,
            detail={
                "code": "IDEMPOTENCY_CONFLICT",
                "message": "This idempotency key was already used with a different request.",
            },
        )
    return record


def record_result(
    db: Session,
    actor: User,
    operation: str,
    key: str,
    fingerprint: str,
    response_body: dict,
    response_status: int = 201,
) -> None:
    db.add(
        IdempotencyRecord(
            actor_id=actor.id,
            operation=operation,
            key=key,
            request_hash=fingerprint,
            response_status=response_status,
            response_body=response_body,
        )
    )
