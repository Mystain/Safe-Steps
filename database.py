from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()
        
def init_db(app):
    app.config.from_object(Config)  # Load configurations from Config class
    db.init_app(app)

    with app.app_context():
        db.create_all()

        
