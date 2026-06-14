from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, current_app
import os
import hashlib
import sqlite3
import getpass
import bcrypt
import re
from flask import g
# file uplaod logic 
from werkzeug.utils import secure_filename
import uuid
from dotenv import load_dotenv
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from database import get_db, close_db
try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


# validates if password matches criteria
def validate_password_only(password,password_2):
    error_message = ""
    reg = r"^(?=(?:[^a-z]*[a-z]){1})(?=(?:[^A-Z]*[A-Z]){1})(?=(?:[^0-9]*[0-9]){1})(?=.*[!-\/:-@\[-`{-~]).{6,20}$"

    pat = re.compile(reg)
    mat = re.search(pat, password)
    if not mat: 
        error_message = "Password need to be between 6 to 20 characters inclusive, with at least 1 upper and lowercase, 1 number and 1 special character."   
        return False, error_message
    if password != password_2: 
        error_message = "Passwords do not match"
        return False, error_message
    return True, error_message

def validate_credentials(email, password, password_2, first_name, last_name):
    error_message = ""
    # assumes all strings
    # incremental 
    
    # Validate email
    pattern = r'^[\w\.-]+@[a-zA-Z\d-]+\.[a-zA-Z]{2,}$'
    
    
    # Use re.fullmatch to ensure the entire string matches the pattern
    if not re.fullmatch(pattern, email.strip()):
        error_message = "Email is invalid"
        return False, error_message

    
    # check password - Source: https://www.geeksforgeeks.org/python/password-validation-in-python/
    # 7 or more characters, 1 number, 1 character, max 20 letters
    # reg = r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{7,20}$"

    #modified version of https://stackoverflow.com/questions/24442564/need-a-regex-for-password-validation-that-allows-all-special-characters, better since it allows more special characters
    reg = r"^(?=(?:[^a-z]*[a-z]){1})(?=(?:[^A-Z]*[A-Z]){1})(?=(?:[^0-9]*[0-9]){1})(?=.*[!-\/:-@\[-`{-~]).{6,20}$"

    pat = re.compile(reg)
    mat = re.search(pat, password)
    if not mat: 
        # make the errror message more clear
        error_message = "Password need to be between 6 to 20 characters inclusive, with at least 1 upper and lowercase, 1 number and 1 special character."   
        return False, error_message
    if password != password_2: 
        error_message = "Passwords do not match"
        return False, error_message
    
    # first_name
    first_name_pattern = r'^(?:[a-zA-Z]+(?:[-\s][a-zA-Z]+)*)$'
    if bool(re.match(first_name_pattern, first_name)) == False: 
        error_message = "First name is invalid"
        return False, error_message
        # check last namer
        
    if bool(re.match(first_name_pattern, last_name)) == False: 
        error_message = "last name is invalid"
        return False, error_message
    conn, cursor = get_db()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    rows = cursor.fetchall()
    close_db()
    
    if rows: 
        error_message = "email already exists"
        return False, error_message
    

    return True, error_message

   
def validate_event(title, date):
    if not title or not date:
        return False, "Title and date are required"
    if len(title) > 500:
        return False, " title must be below 500 characters in length"
    return True, None




# Api routing got too long and unreadable put it here
def insert_event(cursor, title, date, time, location, desc, image):
    """Insert a new event into the events table, return new row id"""
    cursor.execute("""
        INSERT INTO events (title, date, time, location, description, image)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, date, time, location, desc, image))
    return cursor.lastrowid
        




def allowed_file(filename):
    image_file_types = {"png", "jpg", "jpeg", "webp"}
    return "." in filename and filename.rsplit(".", 1)[1].lower() in image_file_types

def save_event_image(file):
    folder_path = os.path.join("frontend", "assets", "events")
    # wasnt loading properly with the folder path but should be fine
    # for production we will likely need to hardcode it within the server file structure
    # i think depending on how hostinger works

    if not file or file.filename == "":
        return None
    if not allowed_file(file.filename):
        return None
    # i had duplicated code here from a rewrite that i deleted guys

    filename = secure_filename(file.filename)
    os.makedirs(folder_path, exist_ok=True)
    file.save(os.path.join(folder_path, filename))
    # another change is to this -- file structure was wrong and the image wasnt being loaded
    return f"/frontend/assets/events/{filename}"

load_dotenv()
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
BASE_URL = "http://127.0.0.1:5000"

def send_verification_email(recipient_email: str, token: str):
    
    link = f"{BASE_URL}/verify_email?token={token}"
    # attach email
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Food Computing Academy account"
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    
    # FORMAT WAS ADAPTED FROM A SONICWALL CONFIRMATION EMAIL LMAO
    html = f"""
    <div style="font-family:sans-serif;max-width:480px;margin:auto;">
        <h2>Almost there!</h2>
        <p>Click below to verify your email and create your account.
           This link expires in <strong>1 hour</strong>.</p>
           
        <a href="{link}" style="display:inline-block;padding:12px 24px;
           background:#2d6a4f;color:#fff;border-radius:6px;text-decoration:none;">
           Verify Email
        </a>
        
        <p style="color:#999;font-size:12px;margin-top:24px;">
            If you didn't request this, ignore this email.
        </p>
    </div>
    """
    # attach again? email format weird 
    # attaches email in container but before attached container i think? 
    # puts html inside email container? @NickKaralis to fact check this laterr
    msg.attach(MIMEText(html, "html"))

    # from sonicwall email - will do documentation next commit
    with smtplib.SMTP("smtp.hostinger.com", 587, timeout=10) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
# NEW: for admin page, i wanted to load recent users or well just users in general
# since a small webwsite i thought this is a cool inlau
def get_users(cursor, query=""):
    if query:
        cursor.execute("""
            SELECT id, first_name, last_name, email, role FROM users
            WHERE CAST(id AS TEXT) = ? OR LOWER(email) LIKE LOWER(?)
            OR LOWER(first_name || ' ' || last_name) LIKE LOWER(?) ORDER BY id ASC """, (query, f'%{query}%', f'%{query}%'))
    else:
        cursor.execute("""
            SELECT id, first_name, last_name, email, role
            FROM users ORDER BY id ASC""")
    columns = [d[0] for d in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

# we no longer need to manually alter through sqlitestudio guys! 
def set_user_role(cursor, target_id, new_role):
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, target_id))
    
STOPWORDS = {
    'a','an','the','and','or','but','in','on','at','to','for',
    'of','with','is','it','this','that','was','are','by','from',
}

def tok(text):
    tokens = re.findall(r'[a-z0-9]+', (text or '').lower())
    return [t for t in tokens if t not in STOPWORDS]

def bm25(q_tokens, corpus):
    if not corpus:
        return []
    if HAS_BM25:
        return BM25Okapi(corpus).get_scores(q_tokens).tolist()
    # plain TF fallback
    def tf(doc):
        freq = {}
        for t in doc: freq[t] = freq.get(t,0)+1
        return sum(freq.get(t,0)/max(len(doc),1) for t in q_tokens)
    return [tf(doc) for doc in corpus]

def snippet(text, q_tokens, length=160):
    lower = (text or '').lower()
    best  = next((lower.find(t) for t in q_tokens if lower.find(t) >= 0), 0)
    start = max(0, best - 55)
    chunk = (text or '')[start:start+length].strip()
    return ('…' if start else '') + chunk + ('…' if start+length < len(text or '') else '')

def rank(rows, q_tokens, text_fields, top=6):
    corpus = [tok(' '.join(str(r.get(f) or '') for f in text_fields)) for r in rows]
    scores = bm25(q_tokens, corpus)
    paired = sorted(zip(scores, rows), key=lambda x: x[0], reverse=True)
    return [r for s, r in paired if s > 0][:top]

ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
ALLOWED_PDF_EXTENSIONS = {"pdf"}

def has_allowed_extension(file, allowed_extensions):
    if not file or not file.filename:
        return False
    return "." in file.filename and file.filename.rsplit(".", 1)[1].lower() in allowed_extensions

def file_under_size_limit(file, max_size):
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size <= max_size

def validate_image_upload(file):
    if not file or file.filename == "":
        return None

    if not has_allowed_extension(file, ALLOWED_IMAGE_EXTENSIONS):
        return "Invalid image type"

    if not file_under_size_limit(file, current_app.config["MAX_IMAGE_SIZE"]):
        return "Image must be under 5 MB"

    return None

def validate_pdf_upload(file):
    if not file or file.filename == "":
        return None

    if not has_allowed_extension(file, ALLOWED_PDF_EXTENSIONS):
        return "Invalid PDF type"

    if not file_under_size_limit(file, current_app.config["MAX_MODULE_PDF_SIZE"]):
        return "PDF must be under 50 MB"

    return None
