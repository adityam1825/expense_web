# personal_finance_manager_web/app.py

import os
from flask import Flask, render_template, request, flash, redirect, url_for, Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, date, UTC # Added UTC here
from sqlalchemy import func
from decimal import Decimal
from flask_migrate import Migrate

# --- Configuration ---
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_super_secret_key_here' # USE A STRONG, RANDOM KEY IN PRODUCTION
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'postgresql://postgres:root%40123@localhost:5432/finance_db' # Corrected: '@' in password is URL-encoded to '%40'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEBUG = os.environ.get('FLASK_DEBUG') == '1'

# --- Database Initialization ---
db = SQLAlchemy()
migrate = Migrate()

# --- Models ---
class Base(db.Model):
    __abstract__ = True
    id = db.Column(db.Integer, primary_key=True)
    # Corrected: Use datetime.now(UTC) and lambda for default
    created_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC))
    # Corrected: Use datetime.now(UTC) and lambda for default and onupdate
    updated_at = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

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

class Category(Base):
    __tablename__ = 'categories'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    type = db.Column(db.String(10), nullable=False) # e.g., 'expense' or 'income'
    __table_args__ = (db.UniqueConstraint('user_id', 'name', name='_user_name_uc'),)
    transactions = db.relationship('Transaction', backref='category', lazy=True)

    def __repr__(self):
        return f"<Category {self.name} (Type: {self.type}, User: {self.user_id})>"

class Transaction(Base):
    __tablename__ = 'transactions'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    # Corrected: Use datetime.now(UTC).date() and lambda for default
    date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(UTC).date())
    type = db.Column(db.String(10), nullable=False) # 'income' or 'expense'
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)

    def __repr__(self):
        return f"<Transaction {self.type}: {self.amount} on {self.date} (User: {self.user_id})>"

class Budget(Base):
    __tablename__ = 'budgets'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_name = db.Column(db.String(100), nullable=False) # Storing name as string
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    # Corrected: Use datetime.now(UTC).date() and lambda for default
    start_date = db.Column(db.Date, nullable=False, default=lambda: datetime.now(UTC).date())
    end_date = db.Column(db.Date, nullable=True)
    __table_args__ = (db.UniqueConstraint('user_id', 'category_name', 'start_date', name='_user_category_start_date_uc'),)

    def __repr__(self):
        return f'<Budget {self.category_name}: ${self.amount}>'

# --- Flask Application Factory ---
def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager = LoginManager()
    login_manager.login_view = 'login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        # db.create_all() # UNCOMMENT THIS ONLY ONCE FOR INITIAL TABLE CREATION IF NOT USING MIGRATIONS, THEN COMMENT OUT AGAIN
        db.create_all()  # Ensure all tables are created

    # --- Routes ---

    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/dashboard')
    @login_required
    def dashboard_page():
        user_id = current_user.id
        today = datetime.now().date()
        start_of_month = today.replace(day=1)
        # Calculate end_of_month as the last day of the current month
        end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)

        total_income = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'income',
            Transaction.date >= start_of_month,
            Transaction.date <= end_of_month
        ).scalar() or Decimal('0.00')

        total_expenses = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= start_of_month,
            Transaction.date <= end_of_month
        ).scalar() or Decimal('0.00')

        net_savings = total_income - total_expenses

        return render_template(
            'reports/dashboard.html',
            user=current_user,
            total_income=total_income,
            total_expenses=total_expenses,
            net_savings=net_savings
        )

    # --- Authentication Routes ---
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard_page'))

        if request.method == 'POST':
            username = request.form.get('username')
            email = request.form.get('email')
            password = request.form.get('password')

            if not username or not password:
                flash('Username and password are required!', 'danger')
                return redirect(url_for('register'))

            user = User.query.filter_by(username=username).first()
            if user:
                flash('Username already taken!', 'danger')
                return redirect(url_for('register'))

            new_user = User(username=username, email=email)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('auth/register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard_page'))

        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')

            user = User.query.filter_by(username=username).first()
            if user and user.check_password(password):
                login_user(user)
                flash('Logged in successfully!', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('dashboard_page'))
            else:
                flash('Invalid username or password.', 'danger')
        return render_template('auth/login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('home'))

    # --- Categories Routes ---
    @app.route('/categories')
    @login_required
    def list_categories():
        categories = Category.query.filter_by(user_id=current_user.id).order_by(Category.name).all()
        return render_template('categories/view_categories.html', categories=categories)

    @app.route('/categories/add', methods=['GET', 'POST'])
    @login_required
    def add_category():
        if request.method == 'POST':
            name = request.form['name'].strip()
            type_ = request.form['type']

            if not name:
                flash('Category name cannot be empty!', 'danger')
                return render_template('categories/add_category.html')

            existing_category = Category.query.filter_by(user_id=current_user.id, name=name).first()
            if existing_category:
                flash(f'Category "{name}" already exists for you!', 'danger')
                return render_template('categories/add_category.html')

            new_category = Category(user_id=current_user.id, name=name, type=type_)
            db.session.add(new_category)
            db.session.commit()
            flash('Category added successfully!', 'success')
            return redirect(url_for('list_categories'))
        return render_template('categories/add_category.html')

    @app.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
    @login_required
    def edit_category(category_id):
        category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
        if request.method == 'POST':
            name = request.form['name'].strip()
            type_ = request.form['type']

            if not name:
                flash('Category name cannot be empty!', 'danger')
                return render_template('categories/edit_category.html', category=category)

            existing_category = Category.query.filter(
                Category.user_id == current_user.id,
                Category.name == name,
                Category.id != category_id
            ).first()

            if existing_category:
                flash(f'Category "{name}" already exists for you!', 'danger')
                return render_template('categories/edit_category.html', category=category)

            category.name = name
            category.type = type_
            db.session.commit()
            flash('Category updated successfully!', 'success')
            return redirect(url_for('list_categories'))
        return render_template('categories/edit_category.html', category=category)

    @app.route('/categories/delete/<int:category_id>', methods=['POST'])
    @login_required
    def delete_category(category_id):
        category = Category.query.filter_by(id=category_id, user_id=current_user.id).first_or_404()
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully!', 'success')
        return redirect(url_for('list_categories'))

    # --- Transactions Routes ---
    @app.route('/transactions')
    @login_required
    def list_transactions():
        all_transactions = Transaction.query.filter_by(user_id=current_user.id).order_by(Transaction.date.desc(), Transaction.created_at.desc()).all()
        return render_template('transactions/list_transactions.html', transactions=all_transactions)

    @app.route('/transactions/add/<transaction_type>', methods=['GET', 'POST'])
    @login_required
    def add_transaction(transaction_type):
        if transaction_type not in ['income', 'expense']:
            flash('Invalid transaction type.', 'danger')
            return redirect(url_for('dashboard_page'))

        categories = Category.query.filter_by(
            user_id=current_user.id,
            type=transaction_type
        ).order_by(Category.name).all()

        if not categories:
            flash(f'Please add at least one {transaction_type} category first!', 'info')
            return redirect(url_for('add_category'))

        today = datetime.now().date()

        if request.method == 'POST':
            try:
                amount = Decimal(request.form['amount'])
                description = request.form.get('description')
                transaction_date_str = request.form['date']
                category_id = request.form['category_id']

                if not amount or amount <= 0:
                    flash('Amount must be a positive number.', 'danger')
                    return render_template(f'transactions/add_{transaction_type}.html', categories=categories, transaction_type=transaction_type, today=today)

                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()

                category = Category.query.filter_by(
                    id=category_id,
                    user_id=current_user.id,
                    type=transaction_type
                ).first()
                if not category:
                    flash('Invalid category selected.', 'danger')
                    return render_template(f'transactions/add_{transaction_type}.html', categories=categories, transaction_type=transaction_type, today=today)

                new_transaction = Transaction(
                    user_id=current_user.id,
                    amount=amount,
                    description=description,
                    date=transaction_date,
                    type=transaction_type,
                    category_id=category.id
                )
                db.session.add(new_transaction)
                db.session.commit()
                flash(f'{transaction_type.capitalize()} added successfully!', 'success')
                return redirect(url_for('list_transactions'))

            except ValueError:
                flash('Invalid amount or date format.', 'danger')
                return render_template(f'transactions/add_{transaction_type}.html', categories=categories, transaction_type=transaction_type, today=today)
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {e}', 'danger')
                return render_template(f'transactions/add_{transaction_type}.html', categories=categories, transaction_type=transaction_type, today=today)

        return render_template(f'transactions/add_{transaction_type}.html', categories=categories, transaction_type=transaction_type, today=today)

    @app.route('/transactions/edit/<int:transaction_id>', methods=['GET', 'POST'])
    @login_required
    def edit_transaction(transaction_id):
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
        categories = Category.query.filter_by(user_id=current_user.id, type=transaction.type).order_by(Category.name).all()

        if request.method == 'POST':
            try:
                amount = Decimal(request.form['amount'])
                description = request.form.get('description')
                transaction_date_str = request.form['date']
                category_id = request.form['category_id']

                if not amount or amount <= 0:
                    flash('Amount must be a positive number.', 'danger')
                    return render_template('transactions/edit_transaction.html', transaction=transaction, categories=categories)

                transaction_date = datetime.strptime(transaction_date_str, '%Y-%m-%d').date()

                category = Category.query.filter_by(id=category_id, user_id=current_user.id, type=transaction.type).first()
                if not category:
                    flash('Invalid category selected.', 'danger')
                    return render_template('transactions/edit_transaction.html', transaction=transaction, categories=categories)

                transaction.amount = amount
                transaction.description = description
                transaction.date = transaction_date
                transaction.category_id = category.id
                db.session.commit()
                flash(f'{transaction.type.capitalize()} updated successfully!', 'success')
                return redirect(url_for('list_transactions'))

            except ValueError:
                flash('Invalid amount or date format.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {e}', 'danger')

        return render_template('transactions/edit_transaction.html', transaction=transaction, categories=categories)

    @app.route('/transactions/delete/<int:transaction_id>', methods=['POST'])
    @login_required
    def delete_transaction(transaction_id):
        transaction = Transaction.query.filter_by(id=transaction_id, user_id=current_user.id).first_or_404()
        db.session.delete(transaction)
        db.session.commit()
        flash(f'{transaction.type.capitalize()} deleted successfully!', 'success')
        return redirect(url_for('list_transactions'))

    # --- Budgets Routes ---
    @app.route('/budgets')
    @login_required
    def list_budgets():
        user_id = current_user.id
        today = datetime.now().date()
        current_month_start = today.replace(day=1)
        next_month_start = (current_month_start + timedelta(days=32)).replace(day=1)

        raw_budgets = Budget.query.filter_by(user_id=user_id).order_by(Budget.start_date.desc()).all()

        budget_data_for_template = []
        for budget in raw_budgets:
            # Calculate spent for the current month for each budget's category
            spent_on_budget_category = db.session.query(func.sum(Transaction.amount)).join(Category).filter(
                Transaction.user_id == user_id,
                Category.user_id == user_id,
                Category.name == budget.category_name,
                Transaction.type == 'expense',
                Transaction.date >= current_month_start, # Calculating spent for current month
                Transaction.date < next_month_start       # within the budget's category
            ).scalar() or Decimal('0.00')

            remaining = budget.amount - spent_on_budget_category
            
            budget_data_for_template.append({
                'id': budget.id, # Keep ID for edit/delete links
                'category_name': budget.category_name,
                'amount': budget.amount,
                'start_date': budget.start_date,
                'end_date': budget.end_date,
                'spent': spent_on_budget_category, # Calculated spent for current month
                'remaining': remaining,            # Calculated remaining for current month
                'status': 'Under Budget' if remaining >= 0 else 'Over Budget'
            })

        return render_template('budgets/view_budgets.html', budgets=budget_data_for_template)


    @app.route('/budgets/add', methods=['GET', 'POST'])
    @login_required
    def add_budget():
        categories = Category.query.filter_by(user_id=current_user.id, type='expense').order_by(Category.name).all()
        if not categories:
            flash('Please add at least one expense category before creating a budget!', 'info')
            return redirect(url_for('add_category'))

        today = datetime.now().date() # Add this line

        if request.method == 'POST':
            try:
                # Changed from category_id to category_name as per template
                category_name = request.form['category_name'].strip()
                amount = Decimal(request.form['amount'])
                start_date_str = request.form['start_date'] # Now required by template
                end_date_str = request.form.get('end_date') # Optional, will be None if not provided

                if not category_name:
                    flash('Category name cannot be empty!', 'danger')
                    return render_template('budgets/add_budget.html', categories=categories, today=today)
                if not amount or amount <= 0:
                    flash('Amount must be a positive number.', 'danger')
                    return render_template('budgets/add_budget.html', categories=categories, today=today)

                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

                if end_date and start_date > end_date:
                    flash('End date cannot be before start date.', 'danger')
                    return render_template('budgets/add_budget.html', categories=categories, today=today)

                existing_budget = Budget.query.filter_by(
                    user_id=current_user.id,
                    category_name=category_name,
                    start_date=start_date
                ).first()

                if existing_budget:
                    flash(f'A budget for "{category_name}" starting on {start_date} already exists.', 'danger')
                    return render_template('budgets/add_budget.html', categories=categories, today=today)

                new_budget = Budget(
                    user_id=current_user.id,
                    category_name=category_name,
                    amount=amount,
                    start_date=start_date,
                    end_date=end_date
                )
                db.session.add(new_budget)
                db.session.commit()
                flash('Budget added successfully!', 'success')
                return redirect(url_for('list_budgets'))

            except ValueError:
                flash('Invalid amount or date format. Ensure dates are valid.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {e}', 'danger')

        return render_template('budgets/add_budget.html', categories=categories, today=today) # Pass today here

    @app.route('/budgets/edit/<int:budget_id>', methods=['GET', 'POST'])
    @login_required
    def edit_budget(budget_id):
        budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
        categories = Category.query.filter_by(user_id=current_user.id, type='expense').order_by(Category.name).all()

        if request.method == 'POST':
            try:
                category_name = request.form['category_name'].strip() # Corrected name
                amount = Decimal(request.form['amount'])
                start_date_str = request.form['start_date'] # Added
                end_date_str = request.form.get('end_date') # Added

                if not category_name:
                    flash('Category name cannot be empty!', 'danger')
                    return render_template('budgets/edit_budget.html', budget=budget, categories=categories)
                if not amount or amount <= 0:
                    flash('Amount must be a positive number.', 'danger')
                    return render_template('budgets/edit_budget.html', budget=budget, categories=categories)

                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None

                if end_date and start_date > end_date:
                    flash('End date cannot be before start date.', 'danger')
                    return render_template('budgets/edit_budget.html', budget=budget, categories=categories)


                existing_budget = Budget.query.filter(
                    Budget.user_id == current_user.id,
                    Budget.category_name == category_name,
                    Budget.start_date == start_date,
                    Budget.id != budget_id
                ).first()

                if existing_budget:
                    flash(f'A budget for "{category_name}" starting on {start_date} already exists.', 'danger')
                    return render_template('budgets/edit_budget.html', budget=budget, categories=categories)

                budget.category_name = category_name
                budget.amount = amount
                budget.start_date = start_date
                budget.end_date = end_date
                db.session.commit()
                flash('Budget updated successfully!', 'success')
                return redirect(url_for('list_budgets'))

            except ValueError:
                flash('Invalid amount or date format. Ensure dates are valid.', 'danger')
            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {e}', 'danger')

        return render_template('budgets/edit_budget.html', budget=budget, categories=categories)

    @app.route('/budgets/delete/<int:budget_id>', methods=['POST'])
    @login_required
    def delete_budget(budget_id):
        budget = Budget.query.filter_by(id=budget_id, user_id=current_user.id).first_or_404()
        db.session.delete(budget)
        db.session.commit()
        flash('Budget deleted successfully!', 'success')
        return redirect(url_for('list_budgets'))

    # --- Reports Routes ---

    @app.route('/reports/summary')
    @login_required
    def monthly_summary_report():
        user_id = current_user.id
        today = datetime.now().date()
        
        # Determine the current year for the dropdown range
        current_year = today.year 
        
        # Get selected year and month from request args, or default to current year/month
        selected_year = request.args.get('year', type=int, default=current_year)
        selected_month = request.args.get('month', type=int, default=today.month)

        # Calculate the start and end dates for the displayed month's data based on selection
        try:
            display_start_of_month = date(selected_year, selected_month, 1)
            # Calculate the first day of the *next* month to get a proper range for filtering
            display_next_month = (display_start_of_month + timedelta(days=32)).replace(day=1)
        except ValueError:
            # Fallback to current month if an invalid year/month combination is selected (e.g., Feb 30)
            flash("Invalid date selection. Showing current month's summary.", "warning")
            display_start_of_month = today.replace(day=1)
            display_next_month = (display_start_of_month + timedelta(days=32)).replace(day=1)
            selected_month = today.month
            selected_year = today.year

        # Calculate total income and expenses for the SELECTED month
        total_income_month = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'income',
            Transaction.date >= display_start_of_month,
            Transaction.date < display_next_month
        ).scalar() or Decimal('0.00')

        total_expense_month = db.session.query(func.sum(Transaction.amount)).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= display_start_of_month,
            Transaction.date < display_next_month
        ).scalar() or Decimal('0.00')

        # Get all income and expense categories for the user
        expense_categories = Category.query.filter_by(user_id=user_id, type='expense').order_by(Category.name).all()
        income_categories = Category.query.filter_by(user_id=user_id, type='income').order_by(Category.name).all()

        # Calculate category-wise spending/income for the SELECTED month
        category_data = []
        for category in expense_categories + income_categories:
            category_total = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == category.id,
                Transaction.date >= display_start_of_month,
                Transaction.date < display_next_month
            ).scalar() or Decimal('0.00')
            category_data.append({
                'name': category.name,
                'type': category.type,
                'total': category_total
            })

        # Get current budgets for the SELECTED month
        current_budgets = Budget.query.filter(
            Budget.user_id == user_id,
            # Check if budget's start date is on or before the current display month
            Budget.start_date <= display_start_of_month, 
            # Check if budget's end date is on or after the current display month, or if it's open-ended
            (Budget.end_date >= display_start_of_month) | (Budget.end_date == None) 
        ).all()

        budget_summary = []
        for budget in current_budgets:
            spent_on_budget_category = db.session.query(func.sum(Transaction.amount)).join(Category).filter(
                Transaction.user_id == user_id,
                Category.user_id == user_id, 
                Category.name == budget.category_name, 
                Transaction.type == 'expense', 
                Transaction.date >= display_start_of_month,
                Transaction.date < display_next_month
            ).scalar() or Decimal('0.00')

            remaining = budget.amount - spent_on_budget_category
            budget_summary.append({
                'category': budget.category_name,
                'budgeted': budget.amount,
                'spent': spent_on_budget_category,
                'remaining': remaining,
                'status': 'Under Budget' if remaining >= 0 else 'Over Budget'
            })

        # Logic to fetch monthly_data for the table (e.g., for the past 12 months from the selected month)
        monthly_data = []
        for i in range(12): # Loop for the last 12 months
            # Calculate the month for the current iteration
            current_iter_month = (display_start_of_month - timedelta(days=30*i)).replace(day=1)
            next_iter_month = (current_iter_month + timedelta(days=32)).replace(day=1)

            month_income = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'income',
                Transaction.date >= current_iter_month,
                Transaction.date < next_iter_month
            ).scalar() or Decimal('0.00')

            month_expense = db.session.query(func.sum(Transaction.amount)).filter(
                Transaction.user_id == user_id,
                Transaction.type == 'expense',
                Transaction.date >= current_iter_month,
                Transaction.date < next_iter_month
            ).scalar() or Decimal('0.00')

            monthly_data.append({
                'month': current_iter_month.strftime('%B %Y'), # Format for display
                'income': month_income,
                'expense': month_expense,
                'net': month_income - month_expense
            })
        monthly_data.reverse() # Display in chronological order (oldest first)

        return render_template(
            'reports/monthly_summary_report.html',
            current_month=display_start_of_month, # The actual month being displayed
            total_income=total_income_month,
            total_expenses=total_expense_month,
            net_savings=total_income_month - total_expense_month,
            category_data=category_data,
            budget_summary=budget_summary,
            monthly_data=monthly_data,          
            current_year=current_year,          
            selected_year=selected_year,        
            selected_month=selected_month       
        )

    @app.route('/reports/expense_breakdown')
    @login_required
    def expense_breakdown_report():
        user_id = current_user.id
        today = datetime.now().date()
        
        # 1. Get current year for dropdown range
        current_year = today.year

        # 2. Get selected filters from request args, default to current month/year, no specific category
        selected_month = request.args.get('month', type=int, default=today.month)
        selected_year = request.args.get('year', type=int, default=current_year)
        
        # 3. Handle category filtering
        selected_category_name = request.args.get('category', default='all')
        
        # Calculate the start and end dates for the displayed month's data based on selection
        try:
            display_start_of_month = date(selected_year, selected_month, 1)
            display_next_month = (display_start_of_month + timedelta(days=32)).replace(day=1)
        except ValueError:
            flash("Invalid date selection. Showing current month's breakdown.", "warning")
            display_start_of_month = today.replace(day=1)
            display_next_month = (display_start_of_month + timedelta(days=32)).replace(day=1)
            selected_month = today.month
            selected_year = today.year

        # Fetch expense categories for the dropdown filter
        expense_categories_for_filter = Category.query.filter_by(user_id=user_id, type='expense').order_by(Category.name).all()

        # Build query for expenses
        expenses_query = db.session.query(Transaction).join(Category).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= display_start_of_month,
            Transaction.date < display_next_month
        )

        # Apply category filter if selected
        if selected_category_name and selected_category_name != 'all':
            expenses_query = expenses_query.filter(Category.name == selected_category_name)
        
        all_expenses = expenses_query.order_by(Transaction.date.desc()).all()

        # Calculate total expense for the selected filters
        total_filtered_expense = db.session.query(func.sum(Transaction.amount)).join(Category).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= display_start_of_month,
            Transaction.date < display_next_month
        )
        if selected_category_name and selected_category_name != 'all':
            total_filtered_expense = total_filtered_expense.filter(Category.name == selected_category_name)
        
        total_filtered_expense = total_filtered_expense.scalar() or Decimal('0.00')


        # Prepare data for charts (e.g., category-wise breakdown for the selected month)
        category_breakdown_query = db.session.query(
            Category.name, 
            func.sum(Transaction.amount)
        ).join(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.type == 'expense',
            Transaction.date >= display_start_of_month,
            Transaction.date < display_next_month
        )
        if selected_category_name and selected_category_name != 'all':
            category_breakdown_query = category_breakdown_query.filter(Category.name == selected_category_name)
        
        category_breakdown_data = category_breakdown_query.group_by(Category.name).all()

        chart_labels = [row[0] for row in category_breakdown_data]
        chart_values = [float(row[1]) for row in category_breakdown_data] # Convert Decimal to float for JS charting

        return render_template(
            'reports/expense_breakdown_report.html',
            all_expenses=all_expenses,
            total_filtered_expense=total_filtered_expense,
            categories_for_filter=expense_categories_for_filter, # For the dropdown
            selected_category_name=selected_category_name,
            selected_month=selected_month,
            selected_year=selected_year,
            current_year=current_year, # For year dropdown range
            chart_labels=chart_labels,
            chart_values=chart_values
        )

    return app

# This block is usually in a run.py or wsgi.py, but for simple apps it's fine here
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)
