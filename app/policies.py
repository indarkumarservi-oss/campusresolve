"""
CampusResolve SLA/Priority Policy Module

This module provides a single source of truth for complaint resolution policies.
It maps priorities to target resolution durations and provides deadline calculation.

All values are in HOURS (not days) for more granular control.
"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from config import Config


# Priority to target resolution hours mapping
# These are illustrative defaults, adjustable by administrators
PRIORITY_TARGET_HOURS: Dict[str, int] = {
    'Critical': 4,
    'High': 24,
    'Medium': 72,
    'Low': 120,
}


def get_target_hours(priority: str) -> int:
    """Get target resolution hours for a priority level."""
    return PRIORITY_TARGET_HOURS.get(priority, 72)


def get_target_days(priority: str) -> int:
    """Get target resolution days for a priority level (for display)."""
    hours = get_target_hours(priority)
    return max(1, round(hours / 24))


def calculate_deadline(created_at: datetime, priority: str) -> datetime:
    """Calculate deadline from creation time and priority."""
    target_hours = get_target_hours(priority)
    return created_at + timedelta(hours=target_hours)


def is_overdue(complaint) -> bool:
    """Check if complaint is overdue based on due_date."""
    if not complaint.due_date:
        return False
    if complaint.status in ['Resolved', 'Closed']:
        return False
    return complaint.due_date < datetime.utcnow()


def get_sla_status(complaint) -> dict:
    """Get detailed SLA status for a complaint."""
    if not complaint.due_date:
        return {'status': 'no_due_date', 'hours_remaining': None, 'overdue': False}

    now = datetime.utcnow()
    if complaint.status in ['Resolved', 'Closed']:
        return {'status': 'completed', 'hours_remaining': 0, 'overdue': False}

    delta = complaint.due_date - now
    hours_remaining = delta.total_seconds() / 3600

    if hours_remaining < 0:
        return {'status': 'overdue', 'hours_remaining': int(hours_remaining), 'overdue': True}
    elif hours_remaining <= 2:
        return {'status': 'critical', 'hours_remaining': int(hours_remaining), 'overdue': False}
    elif hours_remaining <= 24:
        return {'status': 'approaching', 'hours_remaining': int(hours_remaining), 'overdue': False}
    else:
        days = int(hours_remaining / 24)
        return {'status': 'on_track', 'hours_remaining': int(hours_remaining), 'days_remaining': days, 'overdue': False}


def get_escalation_candidates(hours: int = 24):
    """Get complaints needing escalation (overdue or approaching SLA)."""
    now = datetime.utcnow()
    threshold = now + timedelta(hours=hours)

    from app.models.models import Complaint
    from app.extensions import db

    return Complaint.query.filter(
        Complaint.status.in_(['Assigned', 'In Progress', 'Pending Student Response']),
        Complaint.due_date.isnot(None),
        Complaint.due_date <= threshold
    ).order_by(Complaint.due_date).all()