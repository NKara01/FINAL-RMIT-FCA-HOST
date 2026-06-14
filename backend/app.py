from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os
import stripe
from api_routing import register_routes
from database import close_db, get_db
import secrets
app = Flask(__name__, 
            template_folder='../frontend/templates',
            static_folder='../frontend')
# testing
# app.secret_key = os.urandom(24)
app.secret_key = os.getenv("APP_SECRET_KEY")
# print("SECRET KEY===========:", app.secret_key)
app.teardown_appcontext(close_db)

# Upload/request size limits
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["MAX_IMAGE_SIZE"] = 5 * 1024 * 1024
app.config["MAX_MODULE_PDF_SIZE"] = 50 * 1024 * 1024

# Database configuration its prolly wrong path. need to figure out what happened with database splitting?
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database/food_computing_academy_website.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
register_routes(app, db)
# STRIPE KEY TO BE ADDED LATER IN .ENV
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
if not stripe.api_key:
    raise RuntimeError("STRIPE_SECRET_KEY environment variable is not set.")
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)