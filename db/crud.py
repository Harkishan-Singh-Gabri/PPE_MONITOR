from datetime import datetime, timezone
from db.database import get_session
from db.models import Worker, Violation, Alert
from utils.logger import log


def log_violation(worker_id, violation_type, severity,
                  confidence=None, zone="general", snapshot_path=None):
    """Save a violation to DB."""
    session = get_session()
    try:
        v = Violation(
            worker_id      = worker_id,
            violation_type = violation_type,
            severity       = severity,
            confidence     = confidence,
            zone           = zone,
            snapshot_path  = snapshot_path,
            timestamp      = datetime.now(timezone.utc)
        )
        session.add(v)
        session.commit()
        log.debug(f"Violation logged: {worker_id} — {violation_type}")
    except Exception as e:
        session.rollback()
        log.error(f"Failed to log violation: {e}")
    finally:
        session.close()


def log_alert(worker_id, message, severity, violation_type):
    """Save an alert to DB."""
    session = get_session()
    try:
        a = Alert(
            worker_id      = worker_id,
            message        = message,
            severity       = severity,
            violation_type = violation_type,
            timestamp      = datetime.now(timezone.utc)
        )
        session.add(a)
        session.commit()
        log.debug(f"Alert logged: {worker_id} — {violation_type}")
    except Exception as e:
        session.rollback()
        log.error(f"Failed to log alert: {e}")
    finally:
        session.close()


def update_worker(worker_id):
    """Upsert worker last seen timestamp."""
    session = get_session()
    try:
        worker = session.query(Worker).filter_by(worker_id=worker_id).first()
        if worker:
            worker.last_seen = datetime.now(timezone.utc)
        else:
            session.add(Worker(worker_id=worker_id))
        session.commit()
    except Exception as e:
        session.rollback()
        log.error(f"Failed to update worker: {e}")
    finally:
        session.close()


def get_violations(limit=50):
    """Fetch recent violations."""
    session = get_session()
    try:
        return session.query(Violation)\
                      .order_by(Violation.timestamp.desc())\
                      .limit(limit).all()
    finally:
        session.close()


def get_alerts(limit=50):
    """Fetch recent alerts."""
    session = get_session()
    try:
        return session.query(Alert)\
                      .order_by(Alert.timestamp.desc())\
                      .limit(limit).all()
    finally:
        session.close()


def get_compliance_rate():
    """
    Compliance % = workers with no violations / total workers today.
    """
    session = get_session()
    try:
        from sqlalchemy import func, cast, Date
        today = datetime.now(timezone.utc).date()

        total_workers = session.query(
            func.count(func.distinct(Worker.worker_id))
        ).scalar() or 1

        violating_workers = session.query(
            func.count(func.distinct(Violation.worker_id))
        ).filter(
            func.cast(Violation.timestamp, Date) == today
        ).scalar()

        compliance = ((total_workers - violating_workers) / total_workers) * 100
        return round(compliance, 1)
    finally:
        session.close()


if __name__ == "__main__":
    from db.database import init_db
    init_db()

    # test writes
    update_worker("W-01")
    update_worker("W-02")

    log_violation("W-01", "NO-Hardhat", "HIGH", confidence=0.82)
    log_violation("W-02", "Fall-Detected", "CRITICAL", confidence=0.91)
    log_alert("W-01", "WARNING: NO-Hardhat — W-01", "HIGH", "NO-Hardhat")

    # test reads
    violations = get_violations()
    print(f"\nViolations in DB: {len(violations)}")
    for v in violations:
        print(f"  {v.worker_id} — {v.violation_type} — {v.severity} — {v.timestamp}")

    print(f"\nCompliance rate: {get_compliance_rate()}%")