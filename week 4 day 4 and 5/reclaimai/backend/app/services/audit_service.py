import uuid
from sqlalchemy.orm import Session
from app.models.audit_event import AuditEvent
def write_audit(db:Session,actor_id:uuid.UUID|None,action:str,resource_type:str,resource_id:uuid.UUID,changed_fields:dict|None=None)->None:
    db.add(AuditEvent(actor_id=actor_id,action=action,resource_type=resource_type,resource_id=resource_id,changed_fields=changed_fields or {}))
