import re
from datetime import date, datetime, timedelta, timezone
import uuid

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.claim import Claim
from app.models.enums import ClaimStatus, MatchLevel, MatchingStatus, ReportStatus, ReportType
from app.models.item_match import ItemMatch
from app.models.item_report import ItemReport
from app.services.audit_service import write_audit

STOP_WORDS = {"the", "a", "an", "with", "and", "or", "of", "in", "on", "near", "at", "to"}
SYNONYMS = {
    "mobile": "phone",
    "cellphone": "phone",
    "handbag": "bag",
    "purse": "bag",
    "sneakers": "shoe",
    "trainers": "shoe",
}
COLORS = {
    "black", "white", "gray", "grey", "silver", "red", "blue", "green", "yellow",
    "orange", "purple", "pink", "brown", "gold", "beige", "navy",
}
ALGORITHM_VERSION = "rules-v1"


def tokens(value: str | None) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (value or "").casefold())
    return {SYNONYMS.get(word, word) for word in words if word not in STOP_WORDS}


def overlap_score(first: str | None, second: str | None, maximum: int) -> int:
    left, right = tokens(first), tokens(second)
    if not left or not right:
        return 0
    return round(maximum * (2 * len(left & right) / (len(left) + len(right))))


def _description_score(first: str | None, second: str | None) -> int:
    left, right = tokens(first), tokens(second)
    if not left or not right:
        return 0
    return round(10 * len(left & right) / len(left | right))


def date_score(lost: date, found: date) -> int:
    days_later = (found - lost).days
    if days_later < 0:
        return 0
    if days_later == 0:
        return 15
    if days_later <= 2:
        return 12
    if days_later <= 5:
        return 8
    if days_later <= 10:
        return 4
    return 0


def _colour_score(lost: str, found: str) -> int:
    left, right = tokens(lost), tokens(found)
    if left == right and left:
        return 10
    return 5 if (left & right) & COLORS else 0


def _explanation(scores: dict[str, int], lost: ItemReport, found: ItemReport) -> list[str]:
    reasons = ["Same category"]
    reasons.append("Area is a strong match" if scores["location_score"] >= 15 else
                   "Area partially matches" if scores["location_score"] else "Area does not match")
    days = (found.event_date - lost.event_date).days
    reasons.append("Found on the same day" if days == 0 else
                   f"Found {days} day(s) later" if days > 0 else
                   "Found before the lost date")
    reasons.append("Same colour" if scores["colour_score"] == 10 else
                   "Some colour words match" if scores["colour_score"] else "Colour does not match")
    reasons.append("Same brand" if scores["brand_score"] == 10 else
                   "Brand partially matches" if scores["brand_score"] else
                   "Brand not provided" if not lost.brand or not found.brand else "Brand does not match")
    reasons.append("Item names are similar" if scores["name_score"] >= 6 else
                   "Item names partially match" if scores["name_score"] else "Item names do not match")
    reasons.append("Descriptions share details" if scores["description_score"] >= 5 else
                   "Descriptions partially match" if scores["description_score"] else
                   "Descriptions do not match")
    return reasons


def calculate_pair(lost: ItemReport, found: ItemReport) -> dict:
    scores = {
        "category_score": 25 if lost.category_id == found.category_id else 0,
        "location_score": overlap_score(lost.area, found.area, 20),
        "date_score": date_score(lost.event_date, found.event_date),
        "colour_score": _colour_score(lost.colour, found.colour),
        "brand_score": 10 if lost.brand and found.brand and tokens(lost.brand) == tokens(found.brand)
        else 5 if lost.brand and found.brand and tokens(lost.brand) & tokens(found.brand)
        else 0,
        "name_score": overlap_score(lost.item_name, found.item_name, 10),
        "description_score": _description_score(
            f"{lost.description or ''} {lost.distinguishing_features or ''}",
            f"{found.description or ''} {found.distinguishing_features or ''}",
        ),
    }
    total = min(100, sum(scores.values()))
    level = (
        MatchLevel.STRONG if total >= 80 else MatchLevel.POSSIBLE if total >= 60
        else MatchLevel.WEAK if total >= 40 else MatchLevel.HIDDEN
    )
    return {
        **scores,
        "total_score": total,
        "match_level": level,
        "explanation": {"reasons": _explanation(scores, lost, found)},
    }


def _eligible(report: ItemReport) -> bool:
    return report.status in (ReportStatus.ACTIVE, ReportStatus.POTENTIAL_MATCH_FOUND)


def refresh_report_status(db: Session, report: ItemReport, actor_id: uuid.UUID | None = None) -> None:
    if report.status in (ReportStatus.CLOSED, ReportStatus.EXPIRED, ReportStatus.RECOVERED, ReportStatus.RETURNED):
        return
    previous_status = report.status
    claim_in_review = db.scalar(
        select(Claim.id).where(
            or_(Claim.lost_report_id == report.id, Claim.found_report_id == report.id),
            Claim.status.in_([ClaimStatus.UNDER_REVIEW, ClaimStatus.APPROVED]),
        ).limit(1)
    )
    if claim_in_review:
        report.status = ReportStatus.CLAIM_UNDER_REVIEW
    else:
        visible_match = db.scalar(
            select(ItemMatch.id).where(
                ItemMatch.is_active.is_(True),
                ItemMatch.total_score >= 60,
                or_(ItemMatch.lost_report_id == report.id, ItemMatch.found_report_id == report.id),
            ).limit(1)
        )
        report.status = ReportStatus.POTENTIAL_MATCH_FOUND if visible_match else ReportStatus.ACTIVE
    if report.status != previous_status:
        write_audit(
            db,
            actor_id,
            "REPORT_STATUS_CHANGED",
            "ItemReport",
            report.id,
            {"from": previous_status.value, "to": report.status.value},
        )


def recalculate_matches(
    db: Session, report: ItemReport, actor_id: uuid.UUID | None = None
) -> list[ItemMatch]:
    opposite_type = ReportType.FOUND if report.report_type == ReportType.LOST else ReportType.LOST
    candidates = list(
        db.scalars(
            select(ItemReport).where(
                ItemReport.report_type == opposite_type,
                ItemReport.status.in_([ReportStatus.ACTIVE, ReportStatus.POTENTIAL_MATCH_FOUND]),
                ItemReport.category_id == report.category_id,
                ItemReport.reporter_id != report.reporter_id,
            )
        ).all()
    ) if _eligible(report) else []
    eligible_pairs: set[tuple] = set()
    results: list[ItemMatch] = []
    for candidate in candidates:
        lost, found = (report, candidate) if report.report_type == ReportType.LOST else (candidate, report)
        if found.event_date < lost.event_date - timedelta(days=1):
            continue
        pair = (lost.id, found.id)
        eligible_pairs.add(pair)
        values = calculate_pair(lost, found)
        match = db.scalar(
            select(ItemMatch).where(
                ItemMatch.lost_report_id == lost.id,
                ItemMatch.found_report_id == found.id,
            )
        )
        if match is None:
            match = ItemMatch(
                lost_report_id=lost.id,
                found_report_id=found.id,
                match_level=values["match_level"],
            )
        for field, value in values.items():
            setattr(match, field, value)
        match.algorithm_version = ALGORITHM_VERSION
        match.calculated_at = datetime.now(timezone.utc)
        match.is_active = True
        db.add(match)
        results.append(match)

    related_matches = db.scalars(
        select(ItemMatch).where(
            or_(ItemMatch.lost_report_id == report.id, ItemMatch.found_report_id == report.id),
            ItemMatch.is_active.is_(True),
        )
    ).all()
    touched_reports = {report.id: report}
    for match in related_matches:
        pair = (match.lost_report_id, match.found_report_id)
        if pair not in eligible_pairs:
            match.is_active = False
        for related_id in pair:
            related = report if related_id == report.id else db.get(ItemReport, related_id)
            if related is not None:
                touched_reports[related.id] = related
    for match in results:
        for related_id in (match.lost_report_id, match.found_report_id):
            related = report if related_id == report.id else db.get(ItemReport, related_id)
            if related is not None:
                touched_reports[related.id] = related
    db.flush()
    for related in touched_reports.values():
        refresh_report_status(db, related, actor_id)
    report.matching_status = MatchingStatus.COMPLETE
    return results


def deactivate_report_matches(
    db: Session, report: ItemReport, actor_id: uuid.UUID | None = None
) -> None:
    matches = db.scalars(
        select(ItemMatch).where(
            ItemMatch.is_active.is_(True),
            or_(ItemMatch.lost_report_id == report.id, ItemMatch.found_report_id == report.id),
        )
    ).all()
    other_ids = set()
    for match in matches:
        match.is_active = False
        other_ids.add(match.found_report_id if match.lost_report_id == report.id else match.lost_report_id)
    db.flush()
    for other_id in other_ids:
        other = db.get(ItemReport, other_id)
        if other is not None:
            refresh_report_status(db, other, actor_id)
