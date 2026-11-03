import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.core.security import hash_password, verify_verification_answer
from app.dependencies.auth import CurrentUser, DatabaseSession
from app.models.claim import Claim
from app.models.enums import ClaimStatus, ReportStatus, ReportType, UserRole
from app.models.item_match import ItemMatch
from app.models.item_report import ItemReport
from app.schemas.claim import ClaimCreate, ClaimListResponse, ClaimResponse, ClaimReview
from app.services.audit_service import write_audit
from app.services.idempotency_service import record_result, replay_if_present, request_fingerprint
from app.services.matching_service import deactivate_report_matches, refresh_report_status

router=APIRouter(prefix="/api/v1/claims",tags=["Claims"])
ACTIVE_CLAIM_STATUSES=[ClaimStatus.PENDING,ClaimStatus.UNDER_REVIEW,ClaimStatus.APPROVED]
OPEN_REPORT_STATUSES=[ReportStatus.ACTIVE,ReportStatus.POTENTIAL_MATCH_FOUND,ReportStatus.CLAIM_UNDER_REVIEW]


def _not_found() -> HTTPException:
    return HTTPException(404,detail={"code":"NOT_FOUND","message":"Claim was not found or is unavailable."})


def _check_version(claim:Claim,if_match:str|None) -> None:
    if if_match is None:
        raise HTTPException(428,detail={"code":"PRECONDITION_REQUIRED","message":"Send the current claim version in the If-Match header."})
    try:
        supplied=int(if_match.strip().strip('"'))
    except ValueError as exc:
        raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"If-Match must contain the current claim version."}) from exc
    if supplied!=claim.version:
        raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"This claim has changed. Refresh it before trying again."})


@router.post("",response_model=ClaimResponse,status_code=201)
def create_claim(
    data:ClaimCreate,
    response:Response,
    db:DatabaseSession,
    user:CurrentUser,
    idempotency_key:str=Header(...,alias="Idempotency-Key",min_length=16,max_length=128),
):
    operation="POST:/api/v1/claims"
    fingerprint=request_fingerprint(data.model_dump(mode="json"))
    replay=replay_if_present(db,user,operation,idempotency_key,fingerprint)
    if replay is not None:
        response.status_code=replay.response_status
        response.headers["Location"]=f"/api/v1/claims/{replay.response_body['id']}"
        return replay.response_body
    lost=db.get(ItemReport,data.lost_report_id)
    found=db.get(ItemReport,data.found_report_id)
    if (
        lost is None or found is None or lost.report_type!=ReportType.LOST
        or found.report_type!=ReportType.FOUND or lost.reporter_id!=user.id
        or found.reporter_id==user.id or lost.reporter_id==found.reporter_id
    ):
        raise HTTPException(422,detail={"code":"INVALID_CLAIM","message":"A valid lost-and-found match is required."})
    if lost.status not in OPEN_REPORT_STATUSES or found.status not in OPEN_REPORT_STATUSES:
        raise HTTPException(409,detail={"code":"INVALID_TRANSITION","message":"This item is no longer available for claims."})
    match=db.scalar(select(ItemMatch.id).where(
        ItemMatch.lost_report_id==lost.id,
        ItemMatch.found_report_id==found.id,
        ItemMatch.is_active.is_(True),
        ItemMatch.total_score>=60,
    ))
    if match is None:
        raise HTTPException(422,detail={"code":"INVALID_CLAIM","message":"A valid lost-and-found match is required."})
    duplicate=db.scalar(select(Claim.id).where(
        Claim.lost_report_id==lost.id,
        Claim.found_report_id==found.id,
        Claim.claimant_id==user.id,
        Claim.status.in_(ACTIVE_CLAIM_STATUSES),
    ))
    if duplicate:
        raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"An active claim already exists for this match."})
    if not found.verification_answer_hash or not verify_verification_answer(data.verification_answer,found.verification_answer_hash):
        raise HTTPException(422,detail={"code":"VERIFICATION_FAILED","message":"The verification answer does not match."})
    claim=Claim(
        lost_report_id=lost.id,
        found_report_id=found.id,
        claimant_id=user.id,
        ownership_explanation=data.ownership_explanation,
        verification_answer_hash=hash_password(data.verification_answer),
    )
    db.add(claim)
    try:
        db.flush()
        write_audit(db,user.id,"CLAIM_CREATED","Claim",claim.id,{"lost_report_id":str(lost.id),"found_report_id":str(found.id)})
        claim_payload=ClaimResponse.model_validate(claim).model_dump(mode="json")
        record_result(db,user,operation,idempotency_key,fingerprint,claim_payload)
        try:
            db.commit()
        except StaleDataError as exc:
            db.rollback()
            raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"This claim has changed. Refresh it before trying again."}) from exc
    except IntegrityError as exc:
        db.rollback()
        replay=replay_if_present(db,user,operation,idempotency_key,fingerprint)
        if replay is not None:
            response.status_code=replay.response_status
            response.headers["Location"]=f"/api/v1/claims/{replay.response_body['id']}"
            return replay.response_body
        raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"An active claim already exists for this match."}) from exc
    db.refresh(claim)
    response.headers["Location"]=f"/api/v1/claims/{claim.id}"
    return claim


@router.get("",response_model=ClaimListResponse)
def list_claims(
    db:DatabaseSession,
    user:CurrentUser,
    scope:str|None=None,
    status_filter:ClaimStatus|None=Query(None,alias="status"),
    page:int=Query(1,ge=1),
    page_size:int=Query(20,ge=1,le=100),
):
    if scope not in (None,"all"):
        raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"scope must be 'all' when supplied."})
    query=select(Claim)
    if user.role!=UserRole.ADMIN:
        if scope=="all":
            raise HTTPException(403,detail={"code":"FORBIDDEN","message":"Administrator permission is required."})
        query=query.where(or_(
            Claim.claimant_id==user.id,
            Claim.lost_report.has(ItemReport.reporter_id==user.id),
            Claim.found_report.has(ItemReport.reporter_id==user.id),
        ))
    if status_filter:
        query=query.where(Claim.status==status_filter)
    total=db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items=db.scalars(query.order_by(Claim.created_at.desc(),Claim.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items":items,"page":page,"page_size":page_size,"total":total}


@router.get("/{claim_id}",response_model=ClaimResponse)
def get_claim(claim_id:uuid.UUID,db:DatabaseSession,user:CurrentUser):
    claim=db.get(Claim,claim_id)
    if claim is None:
        raise _not_found()
    involved={claim.claimant_id,claim.lost_report.reporter_id,claim.found_report.reporter_id}
    if user.role!=UserRole.ADMIN and user.id not in involved:
        raise _not_found()
    return claim


@router.patch("/{claim_id}/status",response_model=ClaimResponse)
def update_claim_status(
    claim_id:uuid.UUID,
    data:ClaimReview,
    db:DatabaseSession,
    user:CurrentUser,
    if_match:str|None=Header(None,alias="If-Match"),
):
    claim=db.get(Claim,claim_id)
    if claim is None:
        raise _not_found()
    _check_version(claim,if_match)
    if user.role!=UserRole.ADMIN:
        if claim.claimant_id!=user.id or claim.status!=ClaimStatus.PENDING or data.status!=ClaimStatus.CANCELLED:
            raise HTTPException(403,detail={"code":"FORBIDDEN","message":"Only the claimant can cancel a pending claim."})
        if data.review_comment:
            claim.review_comment=data.review_comment
        claim.status=ClaimStatus.CANCELLED
        action="CLAIM_CANCELLED"
    else:
        transitions={
            ClaimStatus.PENDING:{ClaimStatus.UNDER_REVIEW,ClaimStatus.APPROVED,ClaimStatus.REJECTED},
            ClaimStatus.UNDER_REVIEW:{ClaimStatus.APPROVED,ClaimStatus.REJECTED},
            ClaimStatus.APPROVED:{ClaimStatus.REVOKED},
        }
        if data.status not in transitions.get(claim.status,set()):
            raise HTTPException(409,detail={"code":"INVALID_TRANSITION","message":"This claim status transition is not allowed."})
        if data.status in [ClaimStatus.APPROVED,ClaimStatus.REJECTED,ClaimStatus.REVOKED] and not data.review_comment:
            raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"A review comment is required for this decision.","fields":{"review_comment":"Enter the reason for this decision."}})
        claim.status=data.status
        claim.review_comment=data.review_comment
        claim.reviewer_id=user.id
        claim.reviewed_at=datetime.now(timezone.utc)
        action="CLAIM_REVIEWED"
    try:
        claim.version+=1
        db.flush()
        for report in (claim.lost_report,claim.found_report):
            refresh_report_status(db,report,user.id)
        write_audit(db,user.id,action,"Claim",claim.id,{"status":claim.status.value})
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"This claim or one of its reports has changed. Refresh and retry."}) from exc
    db.refresh(claim)
    return claim


@router.post("/{claim_id}/complete",response_model=ClaimResponse)
def complete(claim_id:uuid.UUID,db:DatabaseSession,user:CurrentUser):
    claim=db.get(Claim,claim_id)
    if claim is None:
        raise _not_found()
    lost,found=claim.lost_report,claim.found_report
    if user.role!=UserRole.ADMIN and user.id not in [lost.reporter_id,found.reporter_id]:
        raise HTTPException(403,detail={"code":"FORBIDDEN","message":"You cannot complete this claim."})
    if claim.status!=ClaimStatus.APPROVED:
        raise HTTPException(409,detail={"code":"INVALID_TRANSITION","message":"Only an approved claim can be completed."})
    if lost.status in [ReportStatus.CLOSED,ReportStatus.EXPIRED,ReportStatus.RECOVERED,ReportStatus.RETURNED] or found.status in [ReportStatus.CLOSED,ReportStatus.EXPIRED,ReportStatus.RECOVERED,ReportStatus.RETURNED]:
        raise HTTPException(409,detail={"code":"INVALID_TRANSITION","message":"One of these reports is no longer available."})
    try:
        claim.status=ClaimStatus.COMPLETED
        claim.completed_at=datetime.now(timezone.utc)
        claim.version+=1
        lost.status=ReportStatus.RECOVERED
        lost.version+=1
        found.status=ReportStatus.RETURNED
        found.version+=1
        competitors=db.scalars(select(Claim).where(
            Claim.id!=claim.id,
            or_(Claim.lost_report_id==lost.id,Claim.found_report_id==found.id),
            Claim.status.in_(ACTIVE_CLAIM_STATUSES),
        )).all()
        for other in competitors:
            other.status=ClaimStatus.REJECTED
            other.review_comment="ITEM_UNAVAILABLE: Another claim was completed for this item."
            other.reviewer_id=user.id if user.role==UserRole.ADMIN else None
            other.reviewed_at=datetime.now(timezone.utc)
            other.version+=1
            write_audit(db,user.id,"CLAIM_REJECTED","Claim",other.id,{"reason":"ITEM_UNAVAILABLE"})
        db.flush()
        deactivate_report_matches(db,lost,user.id)
        deactivate_report_matches(db,found,user.id)
        write_audit(db,user.id,"CLAIM_COMPLETED","Claim",claim.id,{"status":ClaimStatus.COMPLETED.value})
        write_audit(db,user.id,"REPORT_STATUS_CHANGED","ItemReport",lost.id,{"status":ReportStatus.RECOVERED.value})
        write_audit(db,user.id,"REPORT_STATUS_CHANGED","ItemReport",found.id,{"status":ReportStatus.RETURNED.value})
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"This claim or one of its reports has changed. Refresh and retry."}) from exc
    db.refresh(claim)
    return claim
