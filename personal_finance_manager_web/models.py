# models.py
from database import db

# Base model that includes common fields like created_at
class Base(db.Model):
    __abstract__ = True # This means Base won't be a table itself

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # You can add common methods here if needed