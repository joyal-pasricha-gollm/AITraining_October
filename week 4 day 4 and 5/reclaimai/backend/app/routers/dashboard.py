from sqlalchemy import func, select

from fastapi import APIRouter

from app.dependencies.auth import AdminUser, CurrentUser, DatabaseSession
from app.models.audit_event import AuditEvent
from app.models.category import Category
from app.models.claim import Claim
from app.models.enums import ClaimStatus, MatchLevel, ReportStatus, ReportType
from app.models.item_match import ItemMatch
from app.models.item_report import ItemReport

router=APIRouter(prefix="/api/v1/dashboard",tags=["Dashboard"])
ACTIVE_STATUSES=[ReportStatus.ACTIVE,ReportStatus.POTENTIAL_MATCH_FOUND,ReportStatus.CLAIM_UNDER_REVIEW]


@router.get("/me")
def me(db:DatabaseSession,user:CurrentUser):
    potential_matches=db.scalar(
        select(func.count()).select_from(ItemMatch).where(
            ItemMatch.lost_report.has(ItemReport.reporter_id==user.id)|
            ItemMatch.found_report.has(ItemReport.reporter_id==user.id),
            ItemMatch.is_active.is_(True),
            ItemMatch.total_score>=60,
        )
    ) or 0
    return {
        "active_reports":db.scalar(select(func.count()).select_from(ItemReport).where(
            ItemReport.reporter_id==user.id,ItemReport.status.in_(ACTIVE_STATUSES)
        )) or 0,
        "potential_matches":potential_matches,
        "pending_claims":db.scalar(select(func.count()).select_from(Claim).where(
            Claim.claimant_id==user.id,Claim.status.in_([ClaimStatus.PENDING,ClaimStatus.UNDER_REVIEW])
        )) or 0,
        "recovered_items":db.scalar(select(func.count()).select_from(ItemReport).where(
            ItemReport.reporter_id==user.id,ItemReport.status==ReportStatus.RECOVERED
        )) or 0,
    }


@router.get("/admin")
def admin(db:DatabaseSession,user:AdminUser):
    category_distribution=db.execute(
        select(Category.id,Category.name,func.count(ItemReport.id))
        .outerjoin(ItemReport,ItemReport.category_id==Category.id)
        .group_by(Category.id,Category.name)
        .order_by(Category.name)
    ).all()
    recent_activity=db.scalars(
        select(AuditEvent).order_by(AuditEvent.occurred_at.desc(),AuditEvent.id.desc()).limit(10)
    ).all()
    return {
        "active_lost":db.scalar(select(func.count()).select_from(ItemReport).where(
            ItemReport.report_type==ReportType.LOST,ItemReport.status.in_(ACTIVE_STATUSES)
        )) or 0,
        "active_found":db.scalar(select(func.count()).select_from(ItemReport).where(
            ItemReport.report_type==ReportType.FOUND,ItemReport.status.in_(ACTIVE_STATUSES)
        )) or 0,
        "strong_matches":db.scalar(select(func.count()).select_from(ItemMatch).where(
            ItemMatch.match_level==MatchLevel.STRONG,ItemMatch.is_active.is_(True)
        )) or 0,
        "pending_claims":db.scalar(select(func.count()).select_from(Claim).where(
            Claim.status.in_([ClaimStatus.PENDING,ClaimStatus.UNDER_REVIEW])
        )) or 0,
        "completed_returns":db.scalar(select(func.count()).select_from(Claim).where(
            Claim.status==ClaimStatus.COMPLETED
        )) or 0,
        "category_distribution":[
            {"category_id":str(category_id),"category":name,"reports":count}
            for category_id,name,count in category_distribution
        ],
        "recent_activity":[
            {
                "action":event.action,
                "resource_type":event.resource_type,
                "occurred_at":event.occurred_at,
                "changed_fields":event.changed_fields,
            }
            for event in recent_activity
        ],
    }
