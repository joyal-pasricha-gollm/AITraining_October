import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_, select

from app.dependencies.auth import CurrentUser, DatabaseSession
from app.models.enums import ReportStatus, UserRole
from app.models.item_match import ItemMatch
from app.models.item_report import ItemReport
from app.schemas.match import MatchResponse
from app.services.audit_service import write_audit
from app.services.matching_service import recalculate_matches

router=APIRouter(prefix="/api/v1/reports",tags=["Matches"])


def _owned_or_admin(report:ItemReport,user) -> bool:
    return report.reporter_id==user.id or user.role==UserRole.ADMIN


@router.get("/{report_id}/matches",response_model=list[MatchResponse])
def matches(
    report_id:uuid.UUID,
    db:DatabaseSession,
    user:CurrentUser,
    minimum_score:int=Query(60,ge=40,le=100),
):
    report=db.get(ItemReport,report_id)
    if report is None or not _owned_or_admin(report,user):
        raise HTTPException(404,detail={"code":"NOT_FOUND","message":"Report was not found or is unavailable."})
    return list(db.scalars(
        select(ItemMatch).where(
            ItemMatch.is_active.is_(True),
            ItemMatch.total_score>=minimum_score,
            or_(ItemMatch.lost_report_id==report_id,ItemMatch.found_report_id==report_id),
        ).order_by(ItemMatch.total_score.desc(),ItemMatch.calculated_at.desc(),ItemMatch.id.desc())
    ).all())


@router.post("/{report_id}/matches/recalculate")
def recalculate(report_id:uuid.UUID,db:DatabaseSession,user:CurrentUser):
    report=db.get(ItemReport,report_id)
    if report is None or not _owned_or_admin(report,user):
        raise HTTPException(404,detail={"code":"NOT_FOUND","message":"Report was not found or is unavailable."})
    if report.status not in [ReportStatus.ACTIVE,ReportStatus.POTENTIAL_MATCH_FOUND]:
        raise HTTPException(409,detail={"code":"INVALID_TRANSITION","message":"Only an active report can be recalculated."})
    results=recalculate_matches(db,report,user.id)
    write_audit(db,user.id,"MATCHES_RECALCULATED","ItemReport",report.id,{"candidate_count":len(results)})
    db.commit()
    return {"report_id":report.id,"candidate_count":len(results),"matching_status":report.matching_status}
