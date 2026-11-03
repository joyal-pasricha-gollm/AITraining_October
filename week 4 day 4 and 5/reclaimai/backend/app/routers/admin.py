from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.dependencies.auth import AdminUser, DatabaseSession
from app.models.enums import ReportStatus, ReportType
from app.models.item_report import ItemReport
from app.schemas.report import AdminReportListResponse
router=APIRouter(prefix="/api/v1/admin",tags=["Administration"])
@router.get("/reports",response_model=AdminReportListResponse)
def reports(
    db:DatabaseSession,
    admin:AdminUser,
    report_type:ReportType|None=None,
    report_status:ReportStatus|None=Query(None,alias="status"),
    page:int=Query(1,ge=1),
    page_size:int=Query(20,ge=1,le=100),
):
    query=select(ItemReport)
    if report_type:query=query.where(ItemReport.report_type==report_type)
    if report_status:query=query.where(ItemReport.status==report_status)
    total=db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items=db.scalars(query.order_by(ItemReport.created_at.desc(),ItemReport.id.desc()).offset((page-1)*page_size).limit(page_size)).all()
    return {"items":items,"page":page,"page_size":page_size,"total":total}
@router.get("/check")
def check(admin:AdminUser):return {"status":"authorized","message":"Administrator access confirmed.","administrator":{"id":str(admin.id),"full_name":admin.full_name,"email":admin.email,"role":admin.role}}
