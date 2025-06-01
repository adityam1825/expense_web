# app.py

# It's good practice to load environment variables as early as possible
# so that other modules that might be imported and rely on them have access.
from dotenv import load_dotenv
load_dotenv()

import os # Import os to access environment variables directly

from flask import Flask, render_template, redirect, url_for, flash
from config import Config # Import your Config class
from database import db # Assuming 'db' is your SQLAlchemy instance
from flask_login import LoginManager, current_user, login_required

from models import User # Import your User model for Flask-Login

# Import your Blueprints
from routes.auth import auth_bp
from routes.budgets import budgets_bp
from routes.categories import categories_bp
# Add other blueprints here as you create them

def create_app():
    """
    Creates and configures the Flask application.
    This function encapsulates the app setup, making it reusable for testing or different environments.
    """
    app = Flask(__name__)

    # Load configuration from the Config object.
    # This sets up general Flask configurations like SECRET_KEY, DEBUG, etc.
    app.config.from_object(Config)

    # Explicitly set SQLALCHEMY_DATABASE_URI using the DATABASE_URL environment variable.
    # This ensures Flask-SQLAlchemy gets the correct URI directly after dotenv has loaded it.
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        # Fallback for local development if DATABASE_URL is not set in .env
        # You might want to raise an error here for production environments
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db' # Example: default to SQLite
        print("WARNING: DATABASE_URL not found in .env. Using default SQLite database.")

    # Recommended: Disable Flask-SQLAlchemy event system to save memory
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize Flask-SQLAlchemy with the app instance.
    # This will now use the SQLALCHEMY_DATABASE_URI explicitly set above.
    db.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login' # Specify the login view for redirection
    login_manager.init_app(app)

    # User loader callback for Flask-Login.
    # This tells Flask-Login how to load a user from the user ID stored in the session.
    @login_manager.user_loader
    def load_user(user_id):
        # Query the User model by ID.
        # The LegacyAPIWarning is an SQLAlchemy 2.0 suggestion;
        # for now, User.query.get() is fine if you're on an older version
        # or haven't migrated fully to SQLAlchemy 2.0 style.
        return User.query.get(int(user_id))

    # --- DATABASE TABLE CREATION ---
    # This block ensures that your database tables are created when the app context is available.
    # It's crucial to run this at least once to set up your database schema.
    # For production, you might use Flask-Migrate for more robust database migrations.
    with app.app_context():
        db.create_all() # Creates tables based on your SQLAlchemy models
    # -------------------------------

    # --- Register Blueprints ---
    # Blueprints organize your application into smaller, reusable components.
    # Each blueprint typically handles a specific set of routes and views.
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(budgets_bp, url_prefix='/budgets')
    app.register_blueprint(categories_bp, url_prefix='/categories')
    # Register any other blueprints you create here

    # --- Global Routes ---
    # These are top-level routes not associated with any specific blueprint.
    @app.route('/')
    def home():
        """Renders the home page."""
        return render_template('home.html')

    @app.route('/dashboard')
    @login_required # Requires user to be logged in to access this page
    def dashboard_page():
        """Renders the user dashboard page."""
        return render_template('reports/dashboard.html', user=current_user)

    # --- Error Handlers ---
    # Custom error pages for common HTTP errors.
    @app.errorhandler(404)
    def page_not_found(e):
        """Handles 404 Not Found errors."""
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        """
        Handles 500 Internal Server Errors.
        Rolls back the database session to ensure no incomplete transactions are committed.
        """
        db.session.rollback() # Important for database integrity on errors
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    # This block runs the Flask development server when the script is executed directly.
    app = create_app() # Get the configured app instance

    # You can add a warning here if the SECRET_KEY is still the default placeholder
    # This is a good reminder for development, but remove or handle differently in production
    if not app.secret_key or app.secret_key == "your_super_secret_key_here_replace_me_with_a_random_string":
        print("WARNING: SECRET_KEY is not set or is using the default placeholder. "
              "Please generate a strong, random SECRET_KEY for production!")

    # Run the Flask application.
    # The 'debug=True' here will override the FLASK_DEBUG environment variable
    # if it's set to False, but it's fine for development.
    app.run(debug=True)
