import datetime
import db

def check_calendar(date_str: str) -> dict:
    """
    Is the center open on date_str (YYYY-MM-DD)?
    
    Error dict not exception — model can
    self-correct from data, not from a 500.
    Weekend check before DB lookup —
    weekends are schedule knowledge not closure rows.
    """
    try:
        d = datetime.date.fromisoformat(date_str)
    except ValueError:
        return {
            "error": f"'{date_str}' is not a valid "
                     f"YYYY-MM-DD date"
        }

    day = d.strftime("%A")

    if d.weekday() >= 5:
        return {
            "date": date_str,
            "day": day,
            "open": False,
            "reason": "Weekend — closed Saturdays and Sundays"
        }

    closure = db.is_closed_on(date_str)
    if closure:
        return {
            "date": date_str,
            "day": day,
            "open": False,
            "reason": closure["name"]
        }

    return {
        "date": date_str,
        "day": day,
        "open": True
    }


def escalate(reason: str, contact: str) -> dict:
    """
    Marker tool — signals escalation needed.
    Does NOT write to DB.
    Harness reads which tools fired
    and does DB writes post-validation.
    
    note field steers model's answer
    at exactly the moment it's composing it.
    """
    return {
        "status": "escalation_noted",
        "reason": reason,
        "contact": contact,
        "note": (
            "Staff will be notified. "
            "Include the contact info in your answer."
        )
    }


def log_gap(question: str) -> dict:
    """
    Marker tool — signals KB couldn't answer.
    Does NOT write to DB.
    Harness sees gap_logged=True and calls
    db.insert_or_increment_gap after validation.
    """
    return {
        "status": "gap_noted",
        "note": (
            "This question was recorded so staff can "
            "add it to the knowledge base. Tell the "
            "parent you've passed it along and offer "
            "the front desk number."
        )
    }