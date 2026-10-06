"""Small first-party activation event writer; caller commits with its business change."""

import uuid

from sqlalchemy.orm import Session

from app.models.product_event import ProductEvent


def track_event(db: Session, name: str, user_id: uuid.UUID,
                workspace_id: uuid.UUID | None = None, *, once: bool = False,
                properties: dict | None = None) -> None:
    if once:
        exists = (db.query(ProductEvent.id)
                  .filter(ProductEvent.user_id == user_id, ProductEvent.name == name)
                  .first())
        if exists:
            return
    db.add(ProductEvent(user_id=user_id, workspace_id=workspace_id,
                        name=name, properties=properties or {}))
