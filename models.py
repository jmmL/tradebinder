import os
import uuid
import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

db = SQLAlchemy()

class Trade(db.Model):
    __tablename__ = 'trades'

    # If we are on Postgres, we can use native UUID. On SQLite, we use String.
    # However, for simplicity and compatibility across both without complex type logic in this script,
    # we'll store it as a String (36 chars) for now, or use a TypeDecorator if we want to be fancy.
    # Given the requirements, String is perfectly fine for ID.
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    creator_mode = db.Column(db.String(10), nullable=False) # 'buy' or 'sell'

    # Storing lists as JSON text.
    # Structure: ["Card A", "Card B"]
    creator_cards = db.Column(db.Text, nullable=False)
    partner_cards = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now())

    def to_dict(self):
        return {
            'id': self.id,
            'creator_mode': self.creator_mode,
            'creator_cards': self.creator_cards,
            'partner_cards': self.partner_cards,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
