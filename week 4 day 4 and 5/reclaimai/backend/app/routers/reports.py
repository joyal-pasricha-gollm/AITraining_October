import uuid
from datetime import date

from fastapi import APIRouter, Header, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import StaleDataError

from app.core.security import hash_verification_answer
from app.dependencies.auth import CurrentUser, DatabaseSession, OptionalCurrentUser
from app.models.category import Category
from app.models.enums import ReportStatus, ReportType, UserRole
from app.models.item_match import ItemMatch
from app.models.item_report import ItemReport
from app.schemas.report import (
    ClaimQuestionResponse,
    PrivateReportListResponse,
    PublicReportResponse,
    ReportCreate,
    ReportListResponse,
    ReportResponse,
    ReportUpdate,
    ReportWithdraw,
)
from app.services.audit_service import write_audit
from app.services.idempotency_service import record_result, replay_if_present, request_fingerprint
from app.services.matching_service import deactivate_report_matches, recalculate_matches

router=APIRouter(prefix="/api/v1/reports",tags=["Reports"])
OPEN_REPORT_STATUSES=[ReportStatus.ACTIVE,ReportStatus.POTENTIAL_MATCH_FOUND,ReportStatus.CLAIM_UNDER_REVIEW]


def _not_found() -> HTTPException:
    return HTTPException(404,detail={"code":"NOT_FOUND","message":"Report was not found or is unavailable."})


def _can_manage(report:ItemReport,user) -> bool:
    return report.reporter_id==user.id or user.role==UserRole.ADMIN


def _check_version(report:ItemReport,if_match:str|None) -> None:
    if if_match is None:
        raise HTTPException(428,detail={"code":"PRECONDITION_REQUIRED","message":"Send the current report version in the If-Match header."})
    try:
        supplied=int(if_match.strip().strip('"'))
    except ValueError as exc:
        raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"If-Match must contain the current report version."}) from exc
    if supplied!=report.version:
        raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"This report has changed. Refresh it before trying again."})


def _report_reference() -> str:
    return f"RA-{uuid.uuid4().int:039d}"


@router.post("",response_model=ReportResponse,status_code=201)
def create_report(
    data:ReportCreate,
    response:Response,
    db:DatabaseSession,
    user:CurrentUser,
    idempotency_key:str=Header(...,alias="Idempotency-Key",min_length=16,max_length=128),
):
    operation="POST:/api/v1/reports"
    fingerprint=request_fingerprint(data.model_dump(mode="json"))
    replay=replay_if_present(db,user,operation,idempotency_key,fingerprint)
    if replay is not None:
        response.status_code=replay.response_status
        response.headers["Location"]=f"/api/v1/reports/{replay.response_body['id']}"
        return replay.response_body
    category=db.get(Category,data.category_id)
    if category is None or not category.is_active:
        raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"Choose an active category."})
    values=data.model_dump(exclude={"verification_answer"})
    values["image_url"]=str(values["image_url"]) if values.get("image_url") else None
    report=ItemReport(
        **values,
        reference=_report_reference(),
        reporter_id=user.id,
        verification_answer_hash=hash_verification_answer(data.verification_answer) if data.verification_answer else None,
    )
    db.add(report)
    try:
        db.flush()
        matches=recalculate_matches(db,report,user.id)
        write_audit(db,user.id,"MATCHES_RECALCULATED","ItemReport",report.id,{"candidate_count":len(matches)})
        write_audit(db,user.id,"REPORT_CREATED","ItemReport",report.id,{"reference":report.reference,"report_type":report.report_type.value})
        report_payload=ReportResponse.model_validate(report).model_dump(mode="json")
        record_result(db,user,operation,idempotency_key,fingerprint,report_payload)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        replay=replay_if_present(db,user,operation,idempotency_key,fingerprint)
        if replay is not None:
            response.status_code=replay.response_status
            response.headers["Location"]=f"/api/v1/reports/{replay.response_body['id']}"
            return replay.response_body
        raise HTTPException(409,detail={"code":"DUPLICATE_RESOURCE","message":"The report could not be saved because a conflicting record exists."}) from exc
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"A related report changed during matching. Retry the request."}) from exc
    db.refresh(report)
    response.headers["Location"]=f"/api/v1/reports/{report.id}"
    return report


@router.get("",response_model=ReportListResponse)
def list_reports(
    db:DatabaseSession,
    report_type:ReportType|None=None,
    category_id:uuid.UUID|None=None,
    colour:str|None=Query(None,max_length=40),
    brand:str|None=Query(None,max_length=80),
    area:str|None=Query(None,max_length=120),
    from_date:date|None=None,
    to_date:date|None=None,
    q:str|None=Query(None,max_length=100),
    page:int=Query(1,ge=1),
    page_size:int=Query(20,ge=1,le=100),
):
    query=select(ItemReport).where(ItemReport.status.in_(OPEN_REPORT_STATUSES))
    if report_type:query=query.where(ItemReport.report_type==report_type)
    if category_id:query=query.where(ItemReport.category_id==category_id)
    if colour:query=query.where(ItemReport.colour.ilike(f"%{colour.strip()}%"))
    if brand:query=query.where(ItemReport.brand.ilike(f"%{brand.strip()}%"))
    if area:query=query.where(ItemReport.area.ilike(f"%{area.strip()}%"))
    if from_date:query=query.where(ItemReport.event_date>=from_date)
    if to_date:query=query.where(ItemReport.event_date<=to_date)
    if from_date and to_date and from_date>to_date:
        raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"from_date must not be after to_date.","fields":{"from_date":"Choose a date on or before to_date."}})
    if q and q.strip():
        term=f"%{q.strip()}%"
        query=query.where(or_(ItemReport.item_name.ilike(term),ItemReport.brand.ilike(term),ItemReport.area.ilike(term),ItemReport.description.ilike(term)))
    total=db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items=db.scalars(query.order_by(ItemReport.created_at.desc(),ItemReport.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items":items,"page":page,"page_size":page_size,"total":total}


@router.get("/mine",response_model=PrivateReportListResponse)
def list_my_reports(
    db:DatabaseSession,
    user:CurrentUser,
    page:int=Query(1,ge=1),
    page_size:int=Query(20,ge=1,le=100),
):
    query=select(ItemReport).where(ItemReport.reporter_id==user.id)
    total=db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items=db.scalars(query.order_by(ItemReport.created_at.desc(),ItemReport.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items":items,"page":page,"page_size":page_size,"total":total}


@router.get("/{report_id}/claim-question",response_model=ClaimQuestionResponse)
def claim_question(
    report_id:uuid.UUID,
    lost_report_id:uuid.UUID,
    db:DatabaseSession,
    user:CurrentUser,
):
    found=db.get(ItemReport,report_id)
    lost=db.get(ItemReport,lost_report_id)
    if (
        found is None or lost is None or found.report_type!=ReportType.FOUND
        or lost.report_type!=ReportType.LOST or lost.reporter_id!=user.id
        or found.reporter_id==user.id or not found.verification_question
        or found.status not in OPEN_REPORT_STATUSES
    ):
        raise _not_found()
    match=db.scalar(select(ItemMatch.id).where(
        ItemMatch.lost_report_id==lost.id,
        ItemMatch.found_report_id==found.id,
        ItemMatch.is_active.is_(True),
        ItemMatch.total_score>=60,
    ))
    if match is None:
        raise _not_found()
    return {"question":found.verification_question}


@router.get("/{report_id}",response_model=ReportResponse|PublicReportResponse)
def get_report(report_id:uuid.UUID,db:DatabaseSession,user:OptionalCurrentUser):
    report=db.get(ItemReport,report_id)
    if report is None:
        raise _not_found()
    return ReportResponse.model_validate(report) if user and _can_manage(report,user) else PublicReportResponse.model_validate(report)


@router.patch("/{report_id}",response_model=ReportResponse)
def update_report(
    report_id:uuid.UUID,
    data:ReportUpdate,
    db:DatabaseSession,
    user:CurrentUser,
    if_match:str|None=Header(None,alias="If-Match"),
):
    report=db.get(ItemReport,report_id)
    if report is None or not _can_manage(report,user):
        raise _not_found()
    if report.status not in [ReportStatus.ACTIVE,ReportStatus.POTENTIAL_MATCH_FOUND]:
        raise HTTPException(409,detail={"code":"INVALID_TRANSITION","message":"This report can no longer be edited."})
    _check_version(report,if_match)
    changes=data.model_dump(exclude_unset=True,exclude={"verification_answer"})
    if not changes and data.verification_answer is None:
        raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"At least one report field must be supplied."})
    if "category_id" in changes:
        category=db.get(Category,changes["category_id"])
        if category is None or not category.is_active:
            raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"Choose an active category."})
    if report.report_type==ReportType.FOUND:
        question=changes.get("verification_question",report.verification_question)
        answer=data.verification_answer if data.verification_answer is not None else report.verification_answer_hash
        if not question or not answer:
            raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"Found reports require a verification question and answer."})
    elif any(changes.get(field) for field in ("verification_question","verification_answer","storage_instructions")):
        raise HTTPException(422,detail={"code":"VALIDATION_ERROR","message":"Private verification and storage fields are only allowed for found reports."})
    for field,value in changes.items():
        if field=="image_url" and value is not None:
            value=str(value)
        setattr(report,field,value)
    if data.verification_answer is not None:
        report.verification_answer_hash=hash_verification_answer(data.verification_answer)
    report.version+=1
    try:
        matches=recalculate_matches(db,report,user.id)
        write_audit(db,user.id,"REPORT_UPDATED","ItemReport",report.id,{"fields":list(data.model_fields_set)})
        write_audit(db,user.id,"MATCHES_RECALCULATED","ItemReport",report.id,{"candidate_count":len(matches)})
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"This report has changed. Refresh it before trying again."}) from exc
    db.refresh(report)
    return report


@router.post("/{report_id}/withdraw",response_model=ReportResponse)
def withdraw(
    report_id:uuid.UUID,
    data:ReportWithdraw,
    db:DatabaseSession,
    user:CurrentUser,
    if_match:str|None=Header(None,alias="If-Match"),
):
    report=db.get(ItemReport,report_id)
    if report is None or not _can_manage(report,user):
        raise _not_found()
    if report.status not in [ReportStatus.ACTIVE,ReportStatus.POTENTIAL_MATCH_FOUND]:
        raise HTTPException(409,detail={"code":"INVALID_TRANSITION","message":"This report can no longer be withdrawn."})
    _check_version(report,if_match)
    report.status=ReportStatus.CLOSED
    report.version+=1
    previous_status=report.status
    deactivate_report_matches(db,report,user.id)
    write_audit(db,user.id,"REPORT_WITHDRAWN","ItemReport",report.id,{"reason_provided":True})
    write_audit(db,user.id,"REPORT_STATUS_CHANGED","ItemReport",report.id,{"from":previous_status.value,"to":report.status.value})
    try:
        db.commit()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(412,detail={"code":"VERSION_CONFLICT","message":"This report has changed. Refresh it before trying again."}) from exc
    db.refresh(report)
    return report
