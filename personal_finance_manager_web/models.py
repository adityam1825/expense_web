# models.py
from database import db
from flask_login import UserMixin
from flask_bcrypt import generate_password_hash, check_password_hash

# Base model for common fields like ID and creation timestamp
class Base(db.Model):
    __abstract__ = True # This means Base itself won't be a database table

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

# --- User Model ---
class User(UserMixin, Base): # UserMixin adds essential properties for Flask-Login
    __tablename__ = 'users' # Explicit database table name

    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False) # Stores the hashed password
    email = db.Column(db.String(100), unique=True) # Optional: Can be nullable=True if not strictly required

    # Define relationships to other tables. 'backref' allows easy access from the other side.
    # 'cascade="all, delete-orphan"' means if a user is deleted, their associated categories, transactions, and budgets are also deleted.
    categories = db.relationship('Category', backref='user', lazy=True, cascade="all, delete-orphan")
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade="all, delete-orphan")
    budgets = db.relationship('Budget', backref='user', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username}>"

    # Flask-Login method: returns the unique ID for the user
    def get_id(self):
        return str(self.id)

    # Helper method to hash passwords
    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')

    # Helper method to check passwords
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


# --- Category Model ---
class Category(Base):
    __tablename__ = 'categories'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False) # e.g., 'expense' or 'income'

    # Ensure a user cannot have two categories with the exact same name
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_name_uc'),)

    transactions = db.relationship('Transaction', backref='category', lazy=True)
    budgets = db.relationship('Budget', backref='category', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Category {self.name} (User: {self.user_id})>"

# --- Transaction Model (for both Income and Expenses) ---
class Transaction(Base):
    __tablename__ = 'transactions'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False) # Stored as a decimal with 2 places
    description = db.Column(db.Text)
    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.String(10), nullable=False) # 'income' or 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True) # Nullable for uncategorized or some income

    def __repr__(self):
        return f"<Transaction {self.type}: {self.amount} on {self.date} for user {self.user_id}>"

# --- Budget Model ---
class Budget(Base):
    __tablename__ = 'budgets'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    month = db.Column(db.Date, nullable=False) # Stored as the first day of the month (e.g., '2025-05-01')
    budget_amount = db.Column(db.Numeric(10, 2), nullable=False)

    # Ensure only one budget per user per category per month
    __table_args__ = (db.UniqueConstraint('user_id', 'category_id', 'month', name='_user_category_month_uc'),)

    def __repr__(self):
        return f"<Budget for {self.category.name} in {self.month.strftime('%Y-%m')}: {self.budget_amount}>"