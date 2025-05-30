# models.py
from database import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Base model for common fields like ID and creation/update timestamps
class Base(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# --- User Model ---
class User(UserMixin, Base):
    __tablename__ = 'users'

    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256), nullable=False)

    categories = db.relationship('Category', backref='user', lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")
    budgets = db.relationship('Budget', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    def get_id(self):
        return str(self.id)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='scrypt')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --- Category Model ---
class Category(Base):
    __tablename__ = 'categories'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False) # e.g., 'expense' or 'income'

    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_name_uc'),)

    transactions = db.relationship('Transaction', backref='category', lazy=True)
    # If you later want to link categories to budgets directly from this side:
    # budgets = db.relationship('Budget', backref='category_rel', lazy=True, cascade="all, delete-orphan")


    def __repr__(self):
        return f"<Category {self.name} (User: {self.user_id})>"


# --- Transaction Model (for both Income and Expenses) ---
class Transaction(Base):
    __tablename__ = 'transactions'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    type = db.Column(db.String(10), nullable=False) # 'income' or 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)

    def __repr__(self):
        return f"<Transaction {self.type}: {self.amount} on {self.date} for user {self.user_id}>"


# --- Budget Model ---
class Budget(Base):
    __tablename__ = 'budgets'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.String(100), nullable=False) # This is the 'category' column causing the error
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    
    # If you want to link budgets directly to the Category model, you'd replace 'category' string field with:
    # category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    # And then you would link to the Category object via 'category_rel' backref
    # category_rel = db.relationship('Category', backref='budgets', lazy=True)

    def __repr__(self):
        return f'<Budget {self.category}: ${self.amount}>'