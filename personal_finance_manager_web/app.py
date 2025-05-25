# app.py
from flask import Flask, render_template
from config import Config # Import your Config class
from database import db # Import the db object from database.py

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config) # Load configuration from Config class

    # Initialize extensions
    db.init_app(app) # Initialize SQLAlchemy with the Flask app

    # Basic route for testing
    @app.route('/')
    def home():
        return "<h1>Hello, Personal Finance Manager!</h1><p>Flask app is running. Database initialized (but no tables created yet).</p>"

    # This part will be used later when you create tables based on models
    # with app.app_context():
    #    db.create_all() # Only run this once to create tables based on your models

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True) # debug=True enables auto-reloading and debug output