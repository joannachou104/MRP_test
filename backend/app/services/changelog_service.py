from sqlalchemy.orm import Session
from app import models


def log(db: Session, action_type: str, target_type: str, target_id: str, operated_by: str, detail: str = "") -> None:
    db.add(
        models.ChangeLog(
            action_type=action_type,
            target_type=target_type,
            target_id=str(target_id),
            detail=detail,
            operated_by=operated_by,
        )
    )
