# Imports

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request
import os
import hashlib
import sqlite3
import getpass
import bcrypt
from flask import session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid
from flask import Flask, render_template, request, g
from flask import g


def get_db():
    if 'db' not in g:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        DB_PATH = os.path.join(BASE_DIR, '..', 'database', 'food_computing_academy_website.db')
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row 
        cursor = g.db.cursor()

    return g.db, cursor

def close_db(error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()
# database_config
    # put database configurations here
    
# database.py



