from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request,abort, jsonify,flash
import validators
import datetime
import os
import hashlib
import sqlite3
import getpass
import bcrypt
import math
import random
from pathlib import Path
from backend_functions import validate_credentials,validate_password_only
from database import get_db, close_db
from flask import session, redirect, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import uuid
from stripe_handler import stripe_url_maker
import secrets
import time
from backend_functions import validate_credentials, validate_event, insert_event, save_event_image, get_users, set_user_role, send_verification_email

from werkzeug.utils import secure_filename
from functools import wraps
import traceback
import stripe
from backend_functions import *
"""
NOTES: 

Login required pages -- 
- You should likely need a login for the blog - either to post or in general
- Modules = Login Only
- Forum = To post
- Programs = Login to sign up for a program. View is fine
    
    
 Add more notes and todo's here guys   
    

"""

"""
Version changes 1/4/26
- Added separators
- added more api routes
- added blog logic
- will add comment logic later
- bugfixing --> YES!

Next commits:
- inshallah i added all the stripe logic :)
- IM THE GOAT

Search bar logic: 
- will start search bar logic on each page as a function in backends. 
- 



Original statements for rollbacks - news: -- Nick
verify email statement: 
# query = "INSERT INTO Users (first_name, last_name, email, password_hash, avatar, bio) VALUES (?, ?, ?, ?, ?, ?) "
# cursor.execute(query, (first_name, last_name, email, password_hash, avatar_url, bio))
# conn.commit() 
# uid = cursor.lastrowid  
# session["user_email"] = email  
# session["user_id"] = uid
# return redirect(url_for("login"))  
"""
# @Config: 
# app = Flask(__name__)

ROLE_STAFF = ("admin", "masteradmin")

def addPopupMessage(message,type = "good"):
    if type != "good" and type != "warning" and type != "bad":
        flash("Error making message!",category = "bad")
        return False
    
    flash(message,category = type)
    return True

def get_user_role(cursor, user_id):
    cursor.execute("SELECT role FROM Users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def can_manage_user(actor_role, target_role):
    # masteradmin manages regular + admin (NOT other masteradmin, NOT self)
    # admin manages regular only -> cannot touch admin or masteradmin
    if actor_role == "masteradmin":
        return target_role in ("regular", "admin")
    if actor_role == "admin":
        return target_role == "regular"
    return False

def delete_user(cursor, user_id):
    # detach this user's content so nothing points at a missing row
    cursor.execute("UPDATE questions        SET author_id = NULL WHERE author_id = ?", (user_id,))
    cursor.execute("UPDATE question_answers SET author_id = NULL WHERE author_id = ?", (user_id,))
    cursor.execute("UPDATE articles         SET author_id = NULL WHERE author_id = ?", (user_id,))
    cursor.execute("UPDATE blog_comments    SET author_id = NULL WHERE author_id = ?", (user_id,))
    cursor.execute("UPDATE news             SET author    = NULL WHERE author    = ?", (user_id,))
    # rows that belong solely to this user — safe to remove
    cursor.execute("DELETE FROM question_votes      WHERE voter_id = ?", (user_id,))
    cursor.execute("DELETE FROM answer_votes        WHERE voter_id = ?", (user_id,))
    cursor.execute("DELETE FROM user_modules        WHERE user_id  = ?", (user_id,))
    cursor.execute("DELETE FROM module_quiz_results WHERE user_id  = ?", (user_id,))
    cursor.execute("DELETE FROM module_part_visited WHERE user_id  = ?", (user_id,))
    cursor.execute("DELETE FROM Users WHERE id = ?", (user_id,))


# rate limiting for logins
def register_routes(app, db): 

    limiter = Limiter(
        app=app, 
        key_func=get_remote_address,
        default_limits=["1000 per day"])
    # app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
    # Database connection

    # ---------------------------------------------------------------------------------------------------


    def app_name_change(new_name): 
        
        app = Flask(new_name)
        return app

# ---------------------------------------------------------------------------------------------------

    @app.route("/")
    @app.route("/index")
    def homepage():
        conn, cursor = get_db()
        cursor.execute(""" SELECT id, title, date, time, location, description, image FROM events ORDER BY date ASC""")
        columns = [d[0] for d in cursor.description]
        events_list = [dict(zip(columns, row)) for row in cursor.fetchall()]



        cursor.execute(""" SELECT id, title, created, company, image_url FROM news ORDER BY created ASC""")
        columns = [d[0] for d in cursor.description]
        news_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        # home page will not rly have any forms on there
        close_db()
        return render_template("homepage.html", events=events_list, news=news_list)


    # with forums likely we will need to get and fetch
    # the actual like comments and questions hence get post
    # will do logic in a second
    # also we will need to store them into the database under USER ID 

    # ---------------------------------------------------------------------------------------------------
    def getPagePost(post_id,questionID):
        max_comments = 5
        conn, cursor = get_db()
        
        query = """SELECT question_answers.id
FROM question_answers
WHERE question_answers.question_id = ?
ORDER BY question_answers.created_at ASC"""
        cursor.execute(query,(questionID,))
        id = cursor.fetchone()
        conn.commit() 

        rows = cursor.fetchall()
        replycount = 0
        page = 1
        for i in rows:
            replycount = replycount + 1
            if str(i[0]) == str(post_id):
                page = math.ceil((replycount + 1)/max_comments)
                break
        ##ADd functionality to get the id of the recently created thread so one can immediately enter it upon creation.
        # cursor.execute("SELECT MAX(questions.id) from questions")
        print("PAGE:", page)
        close_db()
        return page

    def addPost(authorID,title,body,resolved = 0):
        conn, cursor = get_db()
        
        query = "INSERT INTO Questions (author_id,title,body,is_resolved) VALUES (?, ?, ?, ?) RETURNING * "
        print("CREATING QEUSTION", title,"BY:",authorID)
        cursor.execute(query, (authorID,title,body,resolved))
        id = cursor.fetchone()
        conn.commit() 

        ##ADd functionality to get the id of the recently created thread so one can immediately enter it upon creation.
        # cursor.execute("SELECT MAX(questions.id) from questions")
        
        print(id[0])
        close_db()
        return id[0]
    ###TODO: redirect user to the the page where their comment is located in.
    def addComment(questionID,authorID,body,isAccepted = 0):
        conn, cursor = get_db()
        query = "INSERT INTO Question_Answers (question_id,author_id,body,is_accepted) VALUES (?, ?, ?, ?) RETURNING *"
        print("CREATING RESPONSE", body,"IN", questionID,"BY:",authorID)
        cursor.execute(query, (questionID,authorID,body,isAccepted))
        id = cursor.fetchone()
        conn.commit() 

        print(id[0])
        close_db()
        return id[0]
    
    def editComment(postID,body,isAccepted = 0):
        conn, cursor = get_db()
        
        query = """
UPDATE Question_Answers
SET body = ?, is_accepted = ?
WHERE id = ?
"""
        print("EDITING COMMENT ", body)
        cursor.execute(query, (body,isAccepted,postID))
        conn.commit() 

        close_db()

    def editPost(postID,title,body,resolved = 0):
        conn, cursor = get_db()
        
        query = """
UPDATE Questions
SET title = ?, body = ?, is_resolved = ?
WHERE id = ?
"""
        print("EDITING QEUSTION", title)
        cursor.execute(query, (title,body,resolved,postID))
        conn.commit() 

        close_db()
    # fun fact, it doesnt delete it, it just marks it as deleted so everyone can know if someone has been smited. it removes the content though
    # same for questions. It just unlists them and then 
    def deletePost(postID,owner_ID):
        status = 0
        if str(session["user_id"]) == str(owner_ID):
            status = 1
        elif str(session["user_id"]) != str(owner_ID) and session['role'] in ROLE_STAFF:
            status = 2
        
        if status > 0:
            conn, cursor = get_db() 
            query = """
            UPDATE Question_Answers
            SET body = ?, deleted = ?
            WHERE id = ?
            """
            cursor.execute(query, ("",status,postID))
            conn.commit() 
            close_db()
            return True
        return False
    def deleteThread(questionID,owner_ID):
        status = 0
        if str(session["user_id"]) == str(owner_ID):
            status = 1
        elif str(session["user_id"]) != str(owner_ID) and session['role'] in ROLE_STAFF:
            status = 2
        
        if status > 0:
            deltext = "[DELETED BY USER]"
            if status == 2:
                deltext = "[DELETED BY ADMINISTRATOR]"
            conn, cursor = get_db() 
            query = """
            UPDATE questions
            SET body = ?, deleted = ?
            WHERE id = ?
            """
            cursor.execute(query, (deltext,status,questionID))
            conn.commit() 
            close_db()
            return True
        return False


    def getYourThreadVote(threadID,userID,cursor):
        query = """SELECT *
FROM question_votes
WHERE question_votes.voter_id = ? AND question_votes.question_id = ?"""
        cursor.execute(query, (userID,threadID))
        columns = [d[0] for d in cursor.description]
        yourVote = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if not yourVote:
            return "not_voted"
        else:
            yourVote = yourVote[0]
            return yourVote['vote']
    
    def getTotalThreadVote(threadID,cursor):
        query = """SELECT COALESCE(
(SELECT SUM(question_votes.vote)
FROM question_votes
WHERE question_votes.question_id = questions.id), 0) AS "score"
FROM questions
LEFT JOIN question_votes ON question_votes.question_id = questions.id
WHERE questions.id = ?"""
        cursor.execute(query, (threadID,))
        columns = [d[0] for d in cursor.description]
        score = [dict(zip(columns, row)) for row in cursor.fetchall()][0]['score']
        return score
    
    def getTotalAnswerVote(commentID,cursor):
        query = """SELECT COALESCE(SUM(answer_votes.vote), 0) AS "score"
    FROM answer_votes
    WHERE answer_votes.answer_id = ?"""
        cursor.execute(query, (commentID,))
        row = cursor.fetchone()
        return row[0] if row else 0

    def getYourAnswerVote(commentID,userID,cursor):
        query = """SELECT *
FROM answer_votes
WHERE answer_votes.voter_id = ? AND answer_votes.answer_id = ?"""
        cursor.execute(query, (userID,commentID))
        columns = [d[0] for d in cursor.description]
        yourVote = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if not yourVote:
            return 0
        else:
            yourVote = yourVote[0]
            return yourVote['vote']
    #asynchronous upvote/downvote things
    @app.route("/api/comment/<commentID>/vote", methods=["POST"])
    def commentSetVote(commentID):
        data = request.get_json()
        score = int(data["score"])
        if 'user_id' not in session:
            return jsonify({"error": "You're not logged in"}), 401
        if score != 1 and score != 0 and score != -1:
            return jsonify({"error": "you can only put 1 upvote, downvote or remove your vote."}), 400
        new_score2 = score

        conn, cursor = get_db() 
        ### modify your vote
        vote = getYourAnswerVote(commentID,session.get('user_id'),cursor)
        if vote != 0:

            query = """
            UPDATE answer_votes
            SET vote = ?
            WHERE voter_id = ? AND answer_id = ?
            """
            if score == vote:
                new_score2 = 0
                query = """
                DELETE FROM answer_votes
                WHERE voter_id = ? AND answer_id = ?
                """
                cursor.execute(query, (session.get('user_id'),commentID))
            else:
            
                cursor.execute(query, (new_score2,session.get('user_id'),commentID))
        else:
        ### create your vote
            query = """INSERT INTO answer_votes (voter_id,answer_id,vote)
                VALUES (?, ?, ?)"""
            cursor.execute(query, (session.get('user_id'),commentID,score))

        new_score = getTotalAnswerVote(commentID,cursor)
        
        conn.commit() 

        close_db()
        return jsonify({"new_score": new_score,"vote" : new_score2}), 201

    @app.route("/api/thread/<threadID>/vote", methods=["POST"])
    def threadSetVote(threadID):
        data = request.get_json()
        score = int(data["score"])
        if 'user_id' not in session:
            return jsonify({"error": "You're not logged in"}), 401
        if score != 1 and score != 0 and score != -1:
            return jsonify({"error": "you can only put 1 upvote, downvote or remove your vote."}), 400
        new_score2 = score

        conn, cursor = get_db() 
        ### modify your vote
        vote = getYourThreadVote(threadID,session.get('user_id'),cursor)
        if vote != "not_voted":

            query = """
            UPDATE question_votes
            SET vote = ?
            WHERE voter_id = ? AND question_id = ?
            """
            if score == vote:
                new_score2 = 0
                query = """
                DELETE FROM question_votes
                WHERE voter_id = ? AND question_id = ?
                """
                cursor.execute(query, (session.get('user_id'),threadID))
            else:
            
                cursor.execute(query, (new_score2,session.get('user_id'),threadID))
        else:
        ### create your vote
            query = """INSERT INTO question_votes (voter_id,question_id,vote)
                VALUES (?, ?, ?)"""
            cursor.execute(query, (session.get('user_id'),threadID,score))

        new_score = getTotalThreadVote(threadID,cursor)
        
        conn.commit() 

        close_db()
        return jsonify({"new_score": new_score,"vote" : new_score2}), 201


    @app.route("/forum/thread/<threadID>", methods=["GET", "POST"])
    def forumThread(threadID,page=1):
        page = request.args.get('page', 1, type=int)
        max_comments = 5
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        ###DELETING A THREAD
        if request.method == "POST" and "deleteQuestion" in request.form:
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            questionID = str(request.form.get("question_id"))
            authorID = str(request.form.get("author_id"))
            if deleteThread(questionID,authorID):
                addPopupMessage("Successfully deleted thread","good")
            else:
                addPopupMessage("Failed to delete Thread","bad")
            return redirect(url_for('forum'))
        ###DELETING A COMMENT

        if request.method == "POST" and "deleteComment" in request.form: 
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            commentID = str(request.form.get("comment_id"))
            authorID = str(request.form.get("author_id"))
            if deletePost(commentID,authorID):
                addPopupMessage("Successfully deleted comment","good")
            else:
                addPopupMessage("Failed to delete comment","bad")
            return redirect(url_for('forumThread',threadID = threadID,page = page))
        ###POSTING COMMENTS
        if request.method == "POST" and "postComment" in request.form: 
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            reply_body = str(request.form.get("body"))
            author_id = session["user_id"]
            post_id = addComment(threadID,author_id,reply_body)
            newPage = getPagePost(post_id,threadID)
            addPopupMessage("Successfully created comment","good")
            return redirect(url_for('forumThread',threadID = threadID,page = newPage))
        
        ###EDITING YOUR QUESTION
        if request.method == "POST" and "editQuestion" in request.form: 
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            title = str(request.form.get("title"))
            body = str(request.form.get("body"))
            editPost(threadID,title,body)
            addPopupMessage("Successfully edited post","good")
            return redirect(url_for('forumThread',threadID = threadID,page = page))
        ###EDITING YOUR COMMENTS
        if request.method == "POST" and "editComment" in request.form: 
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            commentID = str(request.form.get("comment_id"))
            body = str(request.form.get("body"))
            editComment(commentID,body)
            addPopupMessage("Successfully edited comment","good")
            return redirect(url_for('forumThread',threadID = threadID,page = page))
        conn, cursor = get_db()
        ### construct question
        query = """SELECT questions.title,questions.body,questions.created_at,questions.is_resolved,users.first_name,users.last_name,users.id,users.avatar,questions.deleted,
COALESCE(
(SELECT SUM(question_votes.vote)
FROM question_votes
WHERE question_votes.question_id = questions.id), 0) AS "score"
FROM questions
LEFT JOIN users ON questions.author_id = users.id
LEFT JOIN question_votes ON question_votes.question_id = questions.id
WHERE questions.id = ?"""
        cursor.execute(query,(threadID,),)
        question1 = cursor.fetchone()
        if not question1:
            abort(404)
        question = {
            'title' : question1[0],
            'body' : question1[1],
            'date' : question1[2],
            'is_resolved' : question1[3],
            'author' : {'username': ((question1[4] or "") + " " + (question1[5] or "")).strip() or "[deleted user]"},
            'id' : threadID,
            'user_id' : question1[6],
            'avatar' : question1[7] or "assets/default_avatar.png",
            'deleted' : question1[8],
            'score' : question1[9],
        }
        query = """SELECT users.first_name,users.last_name,question_answers.body,question_answers.is_accepted,
question_answers.created_at,count(*) OVER() AS "full_count",users.id,question_answers.id,users.avatar,question_answers.deleted, 
COALESCE(
(SELECT SUM(answer_votes.vote)
FROM answer_votes
WHERE answer_votes.answer_id = question_answers.id), 0) AS "score"
FROM question_answers
LEFT JOIN users ON question_answers.author_id = users.id
LEFT JOIN answer_votes ON answer_votes.answer_id = question_answers.id
WHERE question_answers.question_id = ?
ORDER BY question_answers.created_at ASC
LIMIT ? OFFSET ?
"""
        cursor.execute(query,(threadID,max_comments,(page-1)*max_comments,))
        replies = [

        ]
        totalComments = 0
        rows = cursor.fetchall()
       ## replycount = 0
        for i in rows:
            ##replycount = replycount + 1
            replies.append({
                'author': {'username': ((i[0] or "") + " " + (i[1] or "")).strip() or "[deleted user]"},
                'body': i[2],
                'is_accepted': i[3],
                'date': i[4],
                'author_id':i[6],
                'post_id':i[7],
                'avatar' : i[8] or "assets/default_avatar.png",
                'deleted' : i[9], #0 = not deleted, #1 = deleted by user, #2 = deleted by admin (if not the same id)
                'score' : i[10],
                'your_vote' : getYourAnswerVote(i[7],session["user_id"],cursor),
            })
            
            totalComments = i[5]
        print("THREADS:" ,totalComments)
        pages = math.ceil(totalComments/max_comments)
        print("PAGES: ", pages)
        question['comments'] = totalComments
        print(question)
        print(replies)

        user_vote = getYourThreadVote(threadID,session.get('user_id'),cursor)
        close_db()
        return render_template("forum_post.html",question = question, replies = replies,page = page,pages = pages,user_vote = user_vote)
    
    @app.route("/forum", methods=["GET", "POST"])
    def forum(page=1):
        page = request.args.get('page', 1, type=int)
        search_query = request.args.get("q", "").strip()
        max_threads = 5

        # If not logged in, automatically redirect to login page; Will display forum page just to see how it is so far visually
        if 'user_id' not in session:
            
            addPopupMessage("You must login first.","bad")
            return redirect(url_for('login'))
        
                 #This becomes a method to create a new post instead, posting replies will be inside it's dedicated thread.
        if request.method == "POST": 
            try: 
                if request.form.get('website'):
                    return redirect(url_for('homepage'))
                post_title = str(request.form.get("title"))
                post_body = str(request.form.get("body"))
                print("ID:" , session["user_id"])
                print(post_title,post_body)
                author_id = session["user_id"]
                postId = addPost(author_id,post_title,post_body)
                addPopupMessage("Successfully created post","good")
                return redirect(url_for('forumThread',threadID = postId))
            except Exception:
                addPopupMessage("Failed to create post","bad")

        conn, cursor = get_db()
        # cursor.execute("INSERT INTO Persons (FirstName, LastName) VALUES (?, ?)", ('John', 'Doe'))

        search_sql = ""
        search_params = []
        if search_query:
            search_sql = " AND (questions.title LIKE ? OR questions.body LIKE ?)"
            search_params = ["%" + search_query + "%", "%" + search_query + "%"]

        query = """
SELECT questions.title,questions.is_resolved,questions.created_at,users.first_name,users.last_name,
(SELECT COUNT(*)
FROM question_answers
WHERE question_answers.question_id = questions.id AND question_answers.deleted = 0) AS "replies"
,questions.id,count(*) OVER() AS "full_count",
                        COALESCE(
(SELECT SUM(question_votes.vote)
FROM question_votes
WHERE question_votes.question_id = questions.id), 0) AS "score"
FROM questions
FULL JOIN users ON questions.author_id = users.id
FULL JOIN question_answers ON questions.id = question_answers.question_id
LEFT JOIN question_votes ON question_votes.question_id = questions.id                       
WHERE questions.title NOT NULL AND questions.deleted = 0
""" + search_sql + """
GROUP BY questions.id
ORDER BY questions.created_at DESC 
                       LIMIT ? OFFSET ?"""
        
        """SELECT SUM(question_votes.vote)
FROM question_votes
WHERE question_votes.question_id = 5"""
        cursor.execute(query,search_params + [max_threads,(page-1)*max_threads])
        
        threads = [
        ]
        totalThreads = 0
        rows = cursor.fetchall()
        for i in rows:
            threads.append({
                'author': {'username': ((i[3] or "") + " " + (i[4] or "")).strip() or "[deleted user]"},
                'title': i[0],
                'date': i[2],
                'time': '15:00',
                'comments': i[5],
                'resolved' : i[1],
                'id' : i[6],
                'score' : i[8]
            })
            totalThreads = i[7]
        ##print(threads)
         
        print("THREADS:" , totalThreads)
        pages = math.ceil(totalThreads/max_threads)
        print("PAGES: ", pages)
        close_db()

                
        # DO LOGIC FOR THE STORING POSTS ETC HERE
        # We can add a ML personality forum post recommender here
        # post_title = ""
        # post_body = ""
        # is_reply = False
        # post_main = True

       
            # if is_reply == 1: 
            #     post_main = False
            # if post_main == True: 
            #     post_title = str(request.form.get("Post_title"))
            #     post_body = str(request.form.get("Post_body"))
                
            # else: 
            #     reply_content = str(request.form.get("reply_body"))
        
        # How to use python dbs guys @everyone
        # cursor.execute("INSERT INTO Persons (FirstName, LastName) VALUES (?, ?)", ('John', 'Doe'))
        # cursor.execute("SELECT * FROM Persons")
        # rows = cursor.fetchall()
        # to push to db use cursor.commit()
        # i used session here so user dosent relogin all the time: <p>Welcome, {{ email }}</p> for html display with jinja
        
        
        return render_template("forum.html",threads = threads,page = page,pages = pages, search_query = search_query)

    #  @team make a note, we will need to add actual cyber security here
    # this is just loading the website


    # ---------------------------------------------------------------------------------------------------



    # login backend logic is here - fetch securely  form db here . 
    @app.route("/login", methods=["GET","POST"])
    @limiter.limit("10 per minute")
    def login():
        if 'user_id' in session:
            addPopupMessage("You have already logged in.","warning")
            return redirect(url_for('homepage'))

        conn, cursor = get_db()


        if request.method == "POST":
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            # fetch entered form stuff
            ALLOW_LOGIN = False
            email = str(request.form.get("email", "")).strip()
            entered_password = str(request.form.get("password"))
            
            
            # if emaol username or password is empty just retry loginpage
            if not email or not entered_password:
                close_db()
                return render_template("login.html", error="All fields are required")
                
            query = "SELECT password_hash FROM Users WHERE email = ?"
            cursor.execute(query, (email,)) 
            record = cursor.fetchone()
            
            if record: 
                hash = record[0]
                entered_password_byte = entered_password.encode('utf-8')
                stored_hash_bytes = record[0] if isinstance(record[0], bytes) else record[0].encode('utf-8')
                
                if bcrypt.checkpw(entered_password_byte, stored_hash_bytes):
                    ALLOW_LOGIN = True
                    query = "SELECT id, role FROM Users WHERE email = ?"
                    cursor.execute(query, (email,))
                    user = cursor.fetchone()

                    session["user_email"] = email
                    session["user_id"] = user[0]
                    session["role"] = user[1]
                else: 
                    ALLOW_LOGIN = False
                    
                    error_message = "Invalid email or password"

            if ALLOW_LOGIN == True: 
                session["user_email"] = email  
                addPopupMessage("Welcome, " + session["user_email"],"good")
                return redirect(url_for("homepage"))  
                
            else: 
                # print that it didnt work
                # post retry again
                error_message = "Invalid email or password"
                addPopupMessage("Invalid email or password.","bad")
                close_db()
                return render_template("login.html", error=error_message)
        close_db()
        return render_template("login.html")

    # ---------------------------------------------------------------------------------------------------
    @app.route('/logout')
    def logout():
        # del session["user_email"]
        # del session["user_id"]
        # del session["role"]
        session.clear()
        addPopupMessage("Logged out successfully","good")

        return redirect(url_for("homepage"))
    # ---------------------------------------------------------------------------------------------------
        # app name
    @app.errorhandler(404)

    # inbuilt function which takes error as parameter
    def not_found(e):
        # defining function
        return render_template("404.html")
    
    # ---------------------------------------------------------------------------------------------------
    # PROFILE SHIT
    def editProfile(id,first_name,last_name,biography,avatar,email):
        conn, cursor = get_db()
        query = """
        UPDATE users
        SET first_name = ?, last_name = ?, bio = ?, email = ?, avatar = ?
        WHERE id = ?
        """
        cursor.execute(query, (first_name,last_name,biography,email,avatar,id))
        conn.commit() 
        close_db()
    
    # EDIT PASSWORD PAGE
    @app.route("/profile/<user_id>/password", methods=["GET","POST"])
    def profilePasswordEdit(user_id):
        messages = {
            'old_password' : "",
            'new_password' : "",
        }
        if 'user_id' not in session:
            return redirect(url_for('login'))
        # yo ucan only change the password of your own account!
        if str(user_id) != str(session.get('user_id')):
            return redirect(url_for('profile',user_id = user_id))
        
        if request.method == "POST" and str(user_id) == str(session.get('user_id')):
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            old_password = str(request.form.get("old_password"))
            new_password = str(request.form.get("new_password"))
            repeat_password = str(request.form.get("repeat_password"))

            conn, cursor = get_db()
            query = "SELECT password_hash FROM Users WHERE id = ?"
            cursor.execute(query, (user_id,)) 
            record = cursor.fetchone()

            entered_password_byte = old_password.encode('utf-8')
            stored_hash_bytes = record[0] if isinstance(record[0], bytes) else record[0].encode('utf-8')
            
            if bcrypt.checkpw(entered_password_byte, stored_hash_bytes):
                canProceed, message = validate_password_only(new_password,repeat_password)
                if canProceed:
                    try:
                        query = """
                        UPDATE users
                        SET password_hash = ?
                        WHERE id = ?
                        """
                        cursor.execute(query, (bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()),user_id))
                        conn.commit() 

                        close_db()
                        addPopupMessage("Password changed successfully","good")
                        return redirect(url_for('profile',user_id = user_id))
                    except Exception:
                        addPopupMessage("An error occurred","bad")
                else:
                    addPopupMessage(message,"bad")
                    messages["new_password"] = message
            else: 
                addPopupMessage("Passwords does not match","bad")
                messages["old_password"] = "Passwords does not match"

            close_db()


        return render_template("change_password.html",messages = messages)
    
    @app.route("/profile/<user_id>", methods=["GET","POST"])
    def profile(user_id):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        conn, cursor = get_db()
        cursor.execute("SELECT id,first_name,last_name,email,created_at,bio,avatar FROM users WHERE users.id = ?", (user_id,))
    
        table = cursor.fetchone()
        if not table:
            abort(404)
        user = {
            "id" : table[0],
            "first_name" : table[1],
            "last_name" : table[2],
            "email" : table[3],
            "created_at" : table[4],
            "biography" : table[5],
            "avatar" : table[6],
        }
        close_db()
        if request.method == "POST" and str(user_id) == str(session.get('user_id')):
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            ##TODO:
            ##If email is changed, redirect to verification page for changing emails instead of immediately confirming the changes
            f = request.files.get("file")
            avatar = user["avatar"]

            if f and f.filename != "":
                error = validate_image_upload(f)
                if error:
                    return render_template("profile_edit.html", user=user, error=error)

                filename = secure_filename(f.filename)
                avatar = "assets/avatars/" + filename

                print("FILENAME:", filename)
                Path("frontend/assets/avatars").mkdir(parents=True, exist_ok=True)
                f.save("frontend/assets/avatars/" + filename)
                
            bio = str(request.form.get("bio"))
            first_name = str(request.form.get("first_name"))
            last_name = str(request.form.get("last_name"))
            email = table[3]
            editProfile(user_id,first_name,last_name,bio,avatar,email)
            addPopupMessage("Profile details changed successfully","good")
            return redirect(url_for('profile',user_id = user_id))
        # if request.method == "POST" and user_id == session.get('user_id') and "editPassword" in request.form:
        #     old_password = str(request.form.get("old_password"))
        #     new_password = str(request.form.get("new_password"))
        #     check_password = str(request.form.get("check_password"))

        #     is_valid2, errormessage2 = validate_password_only(new_password,check_password)
            # email = str(request.form.get("email"))

        return render_template("profile_edit.html", user = user)

    # -------------------------------------------------------------
    #hook this into purchase of module
    def purchaseModule(moduleId,user_id):
        conn, cursor = get_db()
        
        query = "INSERT INTO user_modules (user_id,module_id) VALUES (?,?)"
        cursor.execute(query, (user_id,moduleId,))
        conn.commit() 
        close_db()

    #there will be no cart, considering the payment page code takes in only 1 module id.
    @app.route("/modules/your_modules") 
    def yourModules(page=1):
        max_modules = 16
        page = request.args.get('page', 1, type=int)
        if 'user_id' not in session:
            return redirect(url_for('login'))
        # Will add modules you purchased later on
        #
        conn, cursor = get_db()
        query = """SELECT DISTINCT modules.id,modules.title,modules.description,modules.price,user_modules.purchased_at,user_modules.status,user_modules.progress_percent,user_modules.last_visited_part,user_modules.score,count(*) OVER() AS "full_count",
CASE WHEN (user_modules.last_visited_part IS NOT NULL) THEN module_parts.title  END as "current_part_title"
, modules.image_url
FROM modules
LEFT JOIN user_modules ON modules.id = user_modules.module_id
LEFT JOIN module_parts ON modules.id =  module_parts.module_id
WHERE user_modules.user_id = ? AND (user_modules.last_visited_part IS NULL OR module_parts.id == user_modules.last_visited_part)
        """
        cursor.execute(query,(session.get('user_id'),)) 
        columns = [d[0] for d in cursor.description]
        modules = [dict(zip(columns, row)) for row in cursor.fetchall()]
        pages = 1
        if modules and modules != "":
            for i in modules:
                pages = math.ceil(i["full_count"]/max_modules)
                i["progress_percent"] = getProgress(cursor,session.get('user_id'),i["id"])
        close_db()
        
        return render_template("your_modules.html",modules = modules,page = page, pages = pages)

    @app.route("/modules/view/<module_id>", methods = ["GET","POST"]) 
    def moduleView(module_id):
        id = -1
        if session.get('user_id'):
            id = session.get('user_id')
        if request.method == "POST":
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            if 'user_id' not in session:
                return redirect(url_for('modules'))
            conn, cursor = get_db()
            #if it costs 0, then immediately purchase it. Otherwise redirect to payument page containing the moduleId
            query = """
            SELECT modules.price
            FROM modules
            WHERE modules.id = ?"""
            cursor.execute(query,(module_id,)) 
            cost = cursor.fetchone()[0]
            close_db()

            if cost > 0:
                return redirect(url_for('payment_page',module_id = module_id))
            else:
                try:
                    purchaseModule(module_id,id)
                    addPopupMessage("Purchased module successfully","good")
                except Exception:
                    addPopupMessage("Failed to purchase module","bad")
            
            return redirect(url_for('yourModules'))

        conn, cursor = get_db()

        query = """SELECT DISTINCT modules.id, modules.title, modules.description, modules.price, CASE WHEN EXISTS (
SELECT user_modules2.* FROM user_modules as user_modules2
WHERE user_modules2.user_id == ? AND user_modules2.module_id == modules.id)
       THEN 0
       ELSE 1
  END AS "not_purchased",modules.image_url
FROM modules 
LEFT JOIN user_modules ON user_modules.module_id = modules.id
WHERE modules.id = ?"""
        cursor.execute(query,(id,module_id,)) 
        columns = [d[0] for d in cursor.description]
        module = [dict(zip(columns, row)) for row in cursor.fetchall()][0]

        module_progress = False
        percent_progress = False
        # If purchased, then get details of progress to show on page
        #Note that progress percent will become unused and be changed to take the sum of
        if module["not_purchased"] == 0:
            query = """
    SELECT DISTINCT modules.*,user_modules.purchased_at,user_modules.status,user_modules.progress_percent,user_modules.last_visited_part,user_modules.score,count(*) OVER() AS "full_count",
    CASE WHEN (user_modules.last_visited_part IS NOT NULL) THEN module_parts.title  END as "current_part_title"
    FROM modules
    LEFT JOIN user_modules ON modules.id = user_modules.module_id
    LEFT JOIN module_parts ON modules.id =  module_parts.module_id
    WHERE user_modules.user_id = ? AND (user_modules.last_visited_part IS NULL OR module_parts.id == user_modules.last_visited_part) AND
    modules.id = ?
    """
            cursor.execute(query,(id,module_id,)) 
            columns = [d[0] for d in cursor.description]
            module_progress = [dict(zip(columns, row)) for row in cursor.fetchall()]
            if module_progress:
                module_progress = module_progress[0]
        
                module_progress["progress_percent"] = getProgress(cursor,session.get('user_id'),module_id)
            
        query = """SELECT *
FROM module_parts
WHERE module_parts.module_id = ?"""
        cursor.execute(query,(module_id,)) 
        columns = [d[0] for d in cursor.description]
        parts = [dict(zip(columns, row)) for row in cursor.fetchall()]

        has_final_exam = False
        query = """SELECT *
        FROM module_quizzes
        WHERE module_quizzes.is_final_exam = true AND module_quizzes.module_id = ?"""
        cursor.execute(query,(module_id,)) 
        columns = [d[0] for d in cursor.description]
        temporary = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if temporary and temporary != "" and temporary[0]:
            has_final_exam = True

        close_db()
        return render_template("module_view.html",module = module,parts = parts,has_final_exam = has_final_exam,module_progress = module_progress)
    
    @app.route("/modules", methods = ["GET"]) 
    def modules(page=1):
        page = request.args.get('page', 1, type=int)
        max_modules = 20
        # begin with free modules display. 
        # IS AT DEFAULT: THIS IS TO UPDATE PER DECNELLE RECOMMENDATION GUYS
        # BOW model, decision tree etc or recommender system for the modules based on user attributes can be added here
        
        
            
        
        id = -1
        if session.get('user_id'):
            id = session.get('user_id')
        conn, cursor = get_db()
            
        # add BOW/recommender LOGIC HERE
        ### Get all unpurchased modules
        query = """
        SELECT DISTINCT modules.id,modules.title,modules.description,modules.price, 
        CASE WHEN EXISTS (
SELECT user_modules2.* FROM user_modules as user_modules2
WHERE user_modules2.user_id == ? AND user_modules2.module_id == modules.id)
       THEN 0
       ELSE 1
  END AS "not_purchased"
        ,count(*) OVER() AS "full_count", modules.image_url
        FROM modules
        LEFT JOIN user_modules ON user_modules.module_id = modules.id
        ORDER BY modules.title ASC
        LIMIT ? OFFSET ?
        """
        cursor.execute(query,(id,max_modules,(page-1)*max_modules,)) 
        records = cursor.fetchall()
        
        
        # add display logic for the modules here later as i dont know the format
        # of how we will display modules dynamically.
        columns = [description[0] for description in cursor.description]
        modules = [dict(zip(columns, row)) for row in records]
        
        modules = [dict(zip(columns, row)) for row in records]
        for m in modules:
            if not m["image_url"] or m["image_url"] == "NIL":
                m["image_url"] = "assets/modules/foodcomputingacademy.png"
        
        pages = 1
        for i in records:
            pages = math.ceil(i["full_count"]/max_modules)

            
            # as dencelle is yet to confirm design, i cant finish backend here

        close_db()

        return render_template("modules.html",modules = modules,page = page,pages = pages)
    
    #------ ah yes, the MODULE LOGIC
    # I will have to create a new db table for "visited parts" and dynamically calculate the progress based on that
    # progress is calcualted by the sum of module parts visited and quizzes completed (% grade is used)
    # users can visit any part, but will have to visit a part before visitng their respective quiz.
    # complete module/do final exam will only be avaliable once all parts are done and all quizzes are completed satisfactorily.

    # always do this while db is NOT being accessed!
    def isModulePurchased(module_id,user_id):
        conn, cursor = get_db()
        query = """SELECT *
FROM user_modules
WHERE user_modules.user_id = ? AND user_modules.module_id = ?"""
        cursor.execute(query,(user_id,module_id,)) 
        records = cursor.fetchall()
        close_db()
        if len(records) != 1:
            return False
        else:
            return True
        
    def visitModulePart(user_id,part_id,module_id):
        conn, cursor = get_db()
        query = """
UPDATE user_modules
SET last_visited_part = ?
WHERE module_id = ? AND user_id = ?;

"""
        cursor.execute(query,(part_id,module_id,user_id,)) 
        query = """SELECT *
FROM module_part_visited
WHERE module_part_visited.user_id = ? AND module_part_visited.part_id = ?"""
        cursor.execute(query,(user_id,part_id,)) 
        instance = cursor.fetchone()

        if not instance:
            print("VISITING")
            query = """INSERT INTO module_part_visited (user_id,part_id) VALUES (?, ?) """
            cursor.execute(query,(user_id,part_id,)) 
        else:
            print("ALREADY VISITED!")
        conn.commit() 
        close_db()
    
    def getProgress(cursor,user_id,moduleId):
        query = """SELECT DISTINCT module_parts.id,
                CASE WHEN EXISTS (
SELECT module_visited.* FROM module_part_visited as module_visited
WHERE module_visited.user_id == ? AND module_visited.part_id == module_parts.id)
       THEN 1
       ELSE 0
  END AS "visited"
        , 
        
        (module_quizzes.part_id == module_parts.id) AS "has_quiz", 
        CASE WHEN EXISTS (
SELECT module_quiz2.passed FROM module_quiz_results as module_quiz2
WHERE module_quiz2.quiz_id = module_quiz_results.quiz_id AND  module_quiz2.passed == 1 AND module_quiz2.user_id == ?)
       THEN 1
       ELSE 0
  END AS "quiz_completed"
        FROM module_parts
        LEFT JOIN modules ON module_parts.module_id = modules.id
        LEFT JOIN module_part_visited ON module_part_visited.part_id = module_parts.id
        LEFT JOIN module_quizzes ON module_quizzes.part_id = module_parts.id
        LEFT JOIN module_quiz_results ON module_quiz_results.quiz_id = module_quizzes.id
        WHERE modules.id = ?"""
        cursor.execute(query,(user_id,user_id,moduleId,))
        columns = [d[0] for d in cursor.description]
        module_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        total = 0
        parts_viewed = 0
        quizzes_total = 0
        quizzes_completed = 0
        for i in module_list:
            total = total + 1
            if i["visited"] == 1:
                parts_viewed = parts_viewed + 1
            if i["has_quiz"] == 1:
                quizzes_total = quizzes_total + 1
                if i["quiz_completed"] == 1:
                    quizzes_completed = quizzes_completed + 1
        

        query = """SELECT module_quizzes.*,
        CASE WHEN EXISTS (
SELECT module_quiz2.passed FROM module_quiz_results as module_quiz2
WHERE module_quiz2.quiz_id = module_quiz_results.quiz_id AND  module_quiz2.passed == 1 AND module_quiz2.user_id == ?)
       THEN 1
       ELSE 0
  END AS "quiz_completed"
        FROM module_quizzes
        LEFT JOIN modules ON modules.id = module_quizzes.module_id
        LEFT JOIN module_quiz_results ON module_quiz_results.quiz_id = module_quizzes.id
        WHERE module_quizzes.part_id IS NULL AND
        modules.id = ?"""
        cursor.execute(query,(user_id,moduleId,))
        columns = [d[0] for d in cursor.description]
        final_exam = [dict(zip(columns, row)) for row in cursor.fetchall()]
        if final_exam:
            quizzes_total = quizzes_total + 1
            if final_exam[0]["quiz_completed"]:
                quizzes_completed = quizzes_completed + 1
        # return (parts_viewed + quizzes_completed) * 100/(total + quizzes_total)
        if (total + quizzes_total) == 0:
            return 0
        return (parts_viewed + quizzes_completed) * 100 / (total + quizzes_total)

        
    @app.route("/modules/module/<module_id>")
    def moduleRedirect(module_id):
        # if not logged in, redirect to login
        if 'user_id' not in session:
            return redirect(url_for('login'))
        # if not purchased, redirect to the associated module page
        if not isModulePurchased(module_id,session.get('user_id')):
            return redirect(url_for('moduleView',module_id = module_id))
        conn, cursor = get_db()
                ##get current module you're on
        query = """SELECT user_modules.last_visited_part
        FROM user_modules
        WHERE user_modules.user_id = ? AND user_modules.module_id = ?"""
        cursor.execute(query,(session.get('user_id'),module_id,))
        columns = [d[0] for d in cursor.description]
        content = [dict(zip(columns, row)) for row in cursor.fetchall()][0]
        
        
        if not content['last_visited_part']:
            # get the first module part
            query = """SELECT *
FROM module_parts
WHERE module_parts.module_id = ?"""
            cursor.execute(query,(module_id,))

            columns = [d[0] for d in cursor.description]
            firstModulePart = [dict(zip(columns, row)) for row in cursor.fetchall()][0]
            content['last_visited_part'] = firstModulePart['id']

        close_db()
        return redirect(url_for('modulePart',module_id = module_id, module_part_id = content['last_visited_part']))
        ##otherwise redirect to the first module.

    def canProceed(module_id,user_id,cursor):
         # nav content
        #Get all module part URLs + if visited; janky ass query containing if it has a quiz, if it has been visited and if the quiz has been completed to a satisfactory degree
        query = """SELECT DISTINCT module_parts.title, module_parts.id,module_parts.part_number,
        CASE WHEN EXISTS (
SELECT module_visited.* FROM module_part_visited as module_visited
WHERE module_visited.user_id == ? AND module_visited.part_id == module_parts.id)
       THEN 1
       ELSE 0
  END AS "visited"
        , (module_quizzes.part_id == module_parts.id) AS "has_quiz", 
module_quizzes.id AS "quiz_id", module_quizzes.title AS "quiz_title",
CASE WHEN EXISTS (
SELECT module_quiz2.passed FROM module_quiz_results as module_quiz2
WHERE module_quiz2.quiz_id = module_quiz_results.quiz_id AND  module_quiz2.passed == 1 AND module_quiz2.user_id == ?)
       THEN 1
       ELSE 0
  END AS "quiz_completed",
modules.id as "module_id"
FROM module_parts
LEFT JOIN modules ON module_parts.module_id = modules.id
LEFT JOIN module_part_visited ON module_part_visited.part_id = module_parts.id
LEFT JOIN module_quizzes ON module_quizzes.part_id = module_parts.id
LEFT JOIN module_quiz_results ON module_quiz_results.quiz_id = module_quizzes.id
WHERE modules.id = ?
"""

        cursor.execute(query,(user_id,user_id,module_id,))
        columns = [d[0] for d in cursor.description]
        module_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        quizzes_completed = 0
        parts_completed = 0
        parts = 0
        quizzes = 0

        for i in range(len(module_list)):
            parts = parts + 1

            if module_list[i]["visited"]:
                parts_completed = parts_completed + 1
            if module_list[i]["has_quiz"]:

                quizzes = quizzes + 1
                if module_list[i]["quiz_completed"]:
                    quizzes_completed = quizzes_completed + 1
        canProceed = False
        if quizzes_completed >= quizzes and parts_completed >= parts:
            canProceed = True
        
        return canProceed 

    def getModuleNav(module_id,user_id,module_part_id,cursor):
         # nav content
        #Get all module part URLs + if visited; janky ass query containing if it has a quiz, if it has been visited and if the quiz has been completed to a satisfactory degree
        query = """SELECT DISTINCT module_parts.title, module_parts.id,module_parts.part_number,
        CASE WHEN EXISTS (
SELECT module_visited.* FROM module_part_visited as module_visited
WHERE module_visited.user_id == ? AND module_visited.part_id == module_parts.id)
       THEN 1
       ELSE 0
  END AS "visited"
        , (module_quizzes.part_id == module_parts.id) AS "has_quiz", 
module_quizzes.id AS "quiz_id", module_quizzes.title AS "quiz_title",
CASE WHEN EXISTS (
SELECT module_quiz2.passed FROM module_quiz_results as module_quiz2
WHERE module_quiz2.quiz_id = module_quiz_results.quiz_id AND  module_quiz2.passed == 1 AND module_quiz2.user_id == ?)
       THEN 1
       ELSE 0
  END AS "quiz_completed",
modules.id as "module_id"
FROM module_parts
LEFT JOIN modules ON module_parts.module_id = modules.id
LEFT JOIN module_part_visited ON module_part_visited.part_id = module_parts.id
LEFT JOIN module_quizzes ON module_quizzes.part_id = module_parts.id
LEFT JOIN module_quiz_results ON module_quiz_results.quiz_id = module_quizzes.id
WHERE modules.id = ?
"""

        cursor.execute(query,(user_id,user_id,module_id,))
        columns = [d[0] for d in cursor.description]
        module_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        quizzes_completed = 0
        parts_completed = 0
        parts = 0
        quizzes = 0

        inExam = module_part_id == None

        navigator = {
            "previous_page" : None,
            "previous_title" : None,
            "previous_quiz" : None,
            "current_title" : None,
            "next_page" : None,
            "next_title" : None,
        }
        if inExam:
            navigator["current_title"] = "Exam"
            navigator["previous_page"] = module_list[len(module_list) - 1]["id"]
            navigator["previous_title"] = module_list[len(module_list) - 1]["title"]
            print("previous")
            if module_list[len(module_list) - 1]["has_quiz"]:
                print("previousquiz")
                navigator["previous_quiz"] = module_list[len(module_list) - 1]["quiz_id"]
        for i in range(len(module_list)):
            parts = parts + 1
            print(module_list[i]["id"],module_part_id, i)
            if not inExam:
                if int(module_list[i]["id"]) == int(module_part_id):
                    print("CURRENT PAGE")
                    navigator["current_title"] = module_list[i]["title"]
                    if i > 0:
                        navigator["previous_page"] = module_list[i-1]["id"]
                        navigator["previous_title"] = module_list[i-1]["title"]
                        print("previous")
                        if module_list[i-1]["has_quiz"]:
                            print("previousquiz")
                            navigator["previous_quiz"] = module_list[i-1]["quiz_id"]
                    if i < len(module_list) - 1:
                        navigator["next_page"] = module_list[i+1]["id"]
                        navigator["next_title"] = module_list[i+1]["title"]
            if module_list[i]["visited"]:
                parts_completed = parts_completed + 1
            if module_list[i]["has_quiz"]:

                quizzes = quizzes + 1
                if module_list[i]["quiz_completed"]:
                    quizzes_completed = quizzes_completed + 1
        canProceed = False
        print(quizzes_completed, quizzes)
        print(parts_completed, parts)
        if quizzes_completed >= quizzes and parts_completed >= parts:
            canProceed = True
        #get if it has an exam + if completed
        query = """SELECT module_quizzes.*,
        CASE WHEN EXISTS (
SELECT module_quiz2.passed FROM module_quiz_results as module_quiz2
WHERE module_quiz2.quiz_id = module_quiz_results.quiz_id AND  module_quiz2.passed == 1 AND module_quiz2.user_id == ?)
       THEN 1
       ELSE 0
  END AS "quiz_completed"
FROM module_quizzes
LEFT JOIN modules ON modules.id = module_quizzes.module_id
LEFT JOIN module_quiz_results ON module_quiz_results.quiz_id = module_quizzes.id
WHERE module_quizzes.part_id IS NULL AND
modules.id = ?"""
        cursor.execute(query,(user_id,module_id,))
        columns = [d[0] for d in cursor.description]
        final_exam = [dict(zip(columns, row)) for row in cursor.fetchall()]
        final_quiz = {"exists" : False}
        if final_exam:
            final_quiz = final_exam[0]
            final_quiz["exists"] = True
        return module_list, final_quiz, canProceed, navigator
    

    @app.route("/modules/module/<module_id>/part/<module_part_id>")
    def modulePart(module_id,module_part_id):
        # if not logged in, redirect to login
        if 'user_id' not in session:
            return redirect(url_for('login'))
        # if not purchased, redirect to the associated module page
        if not isModulePurchased(module_id,session.get('user_id')):
            return redirect(url_for('moduleView',module_id = module_id))
        visitModulePart(session.get('user_id'),module_part_id,module_id)
        conn, cursor = get_db()


        # Get module part content
        query = """SELECT modules.title as "module_title", modules.id as "module_id", module_parts.*
FROM modules
LEFT JOIN module_parts ON modules.id = module_parts.module_id
WHERE modules.id = ? AND module_parts.id = ?"""

        
        cursor.execute(query,(module_id,module_part_id,))
        columns = [d[0] for d in cursor.description]
        content = [dict(zip(columns, row)) for row in cursor.fetchall()][0]
        
        cursor.execute(
        "SELECT id, section_type, content, order_num "
        "FROM module_part_sections WHERE part_id = ? ORDER BY order_num ASC",
        (module_part_id,))
        sec_cols = [d[0] for d in cursor.description]
        sections = [dict(zip(sec_cols, r)) for r in cursor.fetchall()]
        
        module_list,final_quiz,canProceed,navigator = getModuleNav(module_id,session.get('user_id'),module_part_id,cursor)
        
        close_db()
        return render_template("module_components/module_part.html",content = content,sections = sections,module_list = module_list,final_quiz = final_quiz, canProceed = canProceed,navigator = navigator)


    @app.route("/modules/module/<module_id>/quiz/<module_part_id>")
    def moduleQuiz(module_id,module_part_id):
        # if not logged in, redirect to login
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # if not purchased, redirect to the associated module page
        if not isModulePurchased(module_id,session.get('user_id')):
            return redirect(url_for('moduleView',module_id = module_id))
        
        conn, cursor = get_db()

        ### get the quiz
        query = """SELECT *
FROM module_quizzes
WHERE module_quizzes.module_id = ? AND module_quizzes.part_id = ?"""
        
        cursor.execute(query,(module_id,module_part_id,))
        columns = [d[0] for d in cursor.description]
        quiz = [dict(zip(columns, row)) for row in cursor.fetchall()][0]
        quiz_id = quiz["id"] 
        
        

        query = """SELECT module_questions.*
FROM module_questions
WHERE module_questions.quiz_id = ?"""
        cursor.execute(query,(quiz_id,))
        columns = [d[0] for d in cursor.description]
        questions = [dict(zip(columns, row)) for row in cursor.fetchall()]

        ### for each question, append all the answers for each
        for question in questions:
            question_id = question["id"]
            query = """SELECT *
FROM module_answers
WHERE module_answers.question_id = ?"""
            cursor.execute(query,(question_id,))
            columns = [d[0] for d in cursor.description]
            answers = [dict(zip(columns, row)) for row in cursor.fetchall()]
            question["answers"] = answers
        
        
        module_list,final_quiz,canProceed,navigator = getModuleNav(module_id,session.get('user_id'),module_part_id,cursor)

        close_db()

        # it will be a complex table:
        # for each question, will have an answer stored in each, via a for loop
        # quiz can be a simple title stuff
        return render_template("module_components/module_quiz.html",quiz = quiz,questions = questions,module_list = module_list,final_quiz = final_quiz, canProceed = canProceed,navigator = navigator)
    

    @app.route("/modules/module/<module_id>/exam")
    def moduleExam(module_id):
        # if not logged in, redirect to login
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        # if not purchased, redirect to the associated module page
        if not isModulePurchased(module_id,session.get('user_id')):
            return redirect(url_for('moduleView',module_id = module_id))

        conn, cursor = get_db()




        ### get the quiz
        query = """SELECT *
FROM module_quizzes
WHERE module_quizzes.module_id = ? AND module_quizzes.part_id IS NULL AND module_quizzes.is_final_exam = 1"""
        
        cursor.execute(query, (module_id,))
        columns = [d[0] for d in cursor.description]
        quizzes = [dict(zip(columns, row)) for row in cursor.fetchall()]

        if not quizzes:
            close_db()
            return redirect(url_for("moduleRedirect", module_id=module_id))

        quiz = quizzes[0]
        quiz_id = quiz["id"]

        ### get the question
        query = """SELECT module_questions.*
FROM module_questions
WHERE module_questions.quiz_id = ?"""
        cursor.execute(query,(quiz_id,))
        columns = [d[0] for d in cursor.description]
        questions = [dict(zip(columns, row)) for row in cursor.fetchall()]

        ### for each question, append all the answers for each
        for question in questions:
            question_id = question["id"]
            query = """SELECT *
FROM module_answers
WHERE module_answers.question_id = ?"""
            cursor.execute(query,(question_id,))
            columns = [d[0] for d in cursor.description]
            answers = [dict(zip(columns, row)) for row in cursor.fetchall()]
            question["answers"] = answers
        
        
        module_list,final_quiz,canProceed,navigator = getModuleNav(module_id,session.get('user_id'),None,cursor)

        # if exam is not ready, rebound back to the last visited module
        

        close_db()
        print(canProceed)
        if not canProceed:
            return redirect(url_for("moduleRedirect",module_id = module_id))

        # it will be a complex table:
        # for each question, will have an answer stored in each, via a for loop
        # quiz can be a simple title stuff
        return render_template("module_components/module_exam.html",quiz = quiz,questions = questions,module_list = module_list,final_quiz = final_quiz, canProceed = canProceed,navigator = navigator)
    
    def createQuizResult(quiz_id,user_id,score,passed,cursor,conn):
        query = """INSERT INTO module_quiz_results
        (user_id,quiz_id,score_percent,passed)
        VALUES (?, ?, ?, ?) 
        """

        cursor.execute(query, (user_id,quiz_id,score,passed))
        conn.commit() 

    @app.route("/modules/module/<module_id>/finish")
    def completeModule(module_id):

        
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not module_id or not isModulePurchased(module_id, session.get('user_id')):
            return redirect(url_for('modules'))
        

        conn, cursor = get_db()

        query = """
        SELECT user_modules.completed_at
        FROM user_modules
        WHERE user_id = ? AND module_id = ?
        """
        cursor.execute(query, (session.get('user_id'),module_id))
        columns = [d[0] for d in cursor.description]
        date = [dict(zip(columns, row)) for row in cursor.fetchall()][0]
        if not date['completed_at']:
            query = """
            UPDATE user_modules
            SET completed_at = (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
            WHERE user_id = ? AND module_id = ?
            """
            cursor.execute(query, (session.get('user_id'),module_id))
            conn.commit()

        progress = getProgress(cursor, session.get('user_id'), module_id)

        query = """SELECT modules.title FROM modules WHERE modules.id = ?"""
        cursor.execute(query, (module_id,))
        module = cursor.fetchone()
        close_db()
        return render_template("module_finish.html", module_id=module_id, module_title=module[0], progress=progress)

    @app.route("/api/quiz/<quiz_id>/check", methods=["POST"])
    def quizEvaluation(quiz_id):
        data = request.get_json()
        print(data)
        module_id = data["module_id"]
        answers = data["responses"]
        if 'user_id' not in session:
            return jsonify({"error": "YOU'RE NOT LOGGED IN!"}), 401
        if not module_id or not isModulePurchased(module_id,session.get('user_id')):
            return jsonify({"error": "YOU'RE HAVERNT PURCHASED THIS MODULE!"}), 401
        print("EVALUATE!")
        

        conn, cursor = get_db()
        query = """SELECT module_answers.*,module_quizzes.pass_percent
FROM module_questions
LEFT JOIN module_answers ON module_answers.question_id = module_questions.id
LEFT JOIN module_quizzes ON module_questions.quiz_id = module_quizzes.id
WHERE module_questions.quiz_id = ?"""

        cursor.execute(query,(quiz_id,))
        columns = [d[0] for d in cursor.description]
        all_answers = [dict(zip(columns, row)) for row in cursor.fetchall()]
        print(all_answers)

        responses = []

        iterator = 0
        passpercent = 100
        correct_answers = 0
        for i in answers:
            for j in all_answers:
                passpercent = j["pass_percent"]
                if i["question_id"] == j["question_id"] and i["answer_id"] == j["id"]:
                    if j["is_correct"] == 1:
                        correct_answers = correct_answers + 1

                    responses.append({
                        "question_id" : i["question_id"],
                        "answer_id" : i["answer_id"],
                        "correct" : j["is_correct"] == 1,
                        "iterator" : iterator,
                    })
                    iterator = iterator + 1
        
        if len(responses) == 0:
            close_db()
            return jsonify({"error": "No responses submitted"}), 400
        has_passed = correct_answers*100/len(responses) >= passpercent
        createQuizResult(quiz_id,session.get('user_id'),correct_answers*100/len(responses),has_passed,cursor,conn)
        print(responses)
        print(has_passed)
        unlockExam = False
        if has_passed:
            unlockExam = canProceed(module_id,session.get('user_id'),cursor)
        close_db()
        return jsonify({"responses" : responses,"has_passed" : has_passed,"unlock_end" : unlockExam}), 201

    # ---------------------------------------------------------------------------------------------------
    # logged in user exclusive news

    @app.route("/events")
    def events():
        conn, cursor = get_db()
        cursor.execute(""" SELECT id, title, date, time, location, description, image FROM events ORDER BY date ASC""")
        columns = [d[0] for d in cursor.description]
        events_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        close_db()

        return render_template("events.html", events=events_list)
    
    #static website that checks if a location is a URL. If a URL, it has a button
    @app.route("/events/<event_id>")
    def eventView(event_id):
        conn, cursor = get_db()
        query = """SELECT *
FROM events
WHERE events.id = ?"""
        cursor.execute(query,(event_id,))
        columns = [d[0] for d in cursor.description]
        event = [dict(zip(columns, row)) for row in cursor.fetchall()][0]
        close_db()
        event_expired = False
        ##TODO: add chekc for if date has past
        date = event['date']
        time = event['time']
        f = '%Y-%m-%d %H:%M'
        date = datetime.datetime.strptime(date + " " + time, f)
        
        now = datetime.datetime.now()
        print(date)
        print(now)
        if now > date:
            event_expired = True


        return render_template("event_view.html", event = event,event_expired = event_expired)

    @app.route("/news")
    def news(): 
        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn, cursor = get_db()
        max_initial_news = 5
        query = """ SELECT n.title, n.body, n.created, u.first_name, u.last_name, n.id,n.image_url FROM news n LEFT JOIN Users u ON n.author = u.id ORDER BY n.created DESC LIMIT ? OFFSET ?"""
        cursor.execute(query,(max_initial_news,0,))
        columns = [d[0] for d in cursor.description]
        news_list = [dict(zip(columns, row)) for row in cursor.fetchall()]
        print(news_list)

        ###WILL REPLACE WITH SOMETHING SMARTER THAN A RANZOMISER LATER
        # featured_news = random.choice(news_list)
        featured_news = random.choice(news_list) if news_list else None
        
        cursor.execute(""" SELECT id, title, date, time, location, description, image FROM events ORDER BY date ASC""")
        columns = [d[0] for d in cursor.description]
        events_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        close_db()
        
        return render_template("news.html", news=news_list, events=events_list,featured_news = featured_news)
    
    @app.route("/news/article/<newsId>", methods=["GET","POST"])
    def newsArticle(newsId):
        if 'user_id' not in session:
            print("YOU CANT DO THAT!")
            return redirect(url_for('login'))
        
                #EDITARTICLE
        if request.method == "POST" and "editNews" in request.form:
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            company = str(request.form.get("company"))
            body = str(request.form.get("body"))
            title = str(request.form.get("title"))
            
            
            # f = request.files['file']
            f = request.files.get("file")
            file = str(request.form.get("old_image"))

            if f and f.filename != "":
                error = validate_image_upload(f)
                if error:
                    # return render_template("news_article.html", error=error)
                    return redirect(url_for("newsArticle", newsId=newsId, error=error))

                filename = secure_filename(f.filename)
                file = "assets/news/" + filename

                print("FILENAME:", filename)
                Path("frontend/assets/news").mkdir(parents=True, exist_ok=True)
                f.save("frontend/assets/news/" + filename)
                
                
                 
            editNews(newsId,title,body,company,file)
            return redirect(url_for('newsArticle',newsId = newsId))
        ###DELETING THE ARTICLE!
        #Note it actually deletes it this time
        if request.method == "POST" and "deleteNews" in request.form:
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            deleteNews(newsId)
            return redirect(url_for('news'))
        
        conn, cursor = get_db()
        cursor.execute(""" SELECT users.first_name,users.last_name,news.title,news.company,news.created,news.body,news.image_url,users.id as "user_id",news.id FROM news
        LEFT JOIN users ON users.id = news.author 
        WHERE news.id = ?""", (newsId,))
        
        news = cursor.fetchone()
        if not news:
            close_db()
            abort(404)
        cursor.execute(""" SELECT id, title, date, time, location, description, image FROM events ORDER BY date ASC""")
        columns = [d[0] for d in cursor.description]
        events_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        close_db()
        article = {
            "author" : ((news[0] or "") + " " + (news[1] or "")).strip() or "[deleted user]",
            "title" : news[2],
            "company" : news[3],
            "date" : news[4],
            "body" : news[5],
            "image_url" : news[6],
            "user_id" : news[7],
            "id" : news[8],
        }
        
        # return render_template("news_article.html", article=article, events=events_list)
        error = request.args.get("error")
        return render_template("news_article.html", article=article, events=events_list, error=error)
    
    
    def editNews(newsID,title,body,company,image_url):
        conn, cursor = get_db()
        
        query = """
UPDATE news
SET title = ?, body = ?,company = ?,image_url = ?
WHERE id = ?;
"""
        print("EDITING COMMENT ", body)
        cursor.execute(query, (title,body,company,image_url,newsID,))
        conn.commit() 

        close_db()
        
    
    def deleteNews(newsID):
        conn, cursor = get_db()
        query = """
        PRAGMA foreign_keys = ON;
        """
        cursor.execute(query)
        query = """
        DELETE FROM news
        WHERE id = ?;
        """
        cursor.execute(query, (newsID,))
        conn.commit() 

        close_db()

    # ---------------------------------------------------------------------------------------------------
    # BLOGS/ARTICLES - AKA news for the unregistered
    # the main page will literally be a 1-1 recreation of the news page, albeit with comments markers similar to a forum for blogs
    # only admins can make blogs, it will be part of the "create blog or article" section in the admin tab later on.



    @app.route("/blogs")
    def blog(page=1): ##yes it will have pagination in case there are tons of blogs published on that page
        page = request.args.get('page', 1, type=int)
        max_articles = 5
        conn, cursor = get_db()
        query = """SELECT articles.id, articles.title, articles.body, articles.company, articles.created, articles.image_url, users.first_name, users.last_name, COUNT(blog_comments.article_id ) FILTER(WHERE blog_comments.deleted == 0) AS "comments",count(*) OVER() AS "full_count", articles.enable_comments
FROM articles
LEFT JOIN users  ON articles.author_id = users.id
LEFT JOIN blog_comments ON articles.id = blog_comments.article_id
WHERE articles.title NOT NULL
GROUP BY articles.id
ORDER BY articles.created DESC
LIMIT ? OFFSET ?
"""

        cursor.execute(query,(max_articles,max_articles*(page-1),))

        

        columns = [d[0] for d in cursor.description]
        articles = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        ## LATER ON, replace the randomizer with a proper featuring function
        featured_article = random.choice(articles) if articles else None
        
        cursor.execute(""" SELECT id, title, date, time, location, description, image FROM events ORDER BY date ASC""")
        columns = [d[0] for d in cursor.description]
        events_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        close_db()
        
        return render_template("blog.html", articles=articles, events=events_list,featured_article = featured_article,page=page)
    
    # Pages are for comments pagination
    @app.route("/blogs/article/<articleId>", methods=["GET","POST"])
    @limiter.limit("20 per minute")
    def blogOrArticlePage(articleId,page=1):
        page = request.args.get('page', 1, type=int)
        max_comments = 5

        #EDITARTICLE
        if request.method == "POST" and "editArticle" in request.form:
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            company = str(request.form.get("company"))
            body = str(request.form.get("body"))
            title = str(request.form.get("title"))
            
            
            f = request.files.get("file")
            file = str(request.form.get("old_image"))

            if f and f.filename != "":
                error = validate_image_upload(f)
                if error:
                    return render_template("blog.html", error=error)

                filename = secure_filename(f.filename)
                file = "assets/news/" + filename

                print("FILENAME:", filename)
                Path("frontend/assets/news").mkdir(parents=True, exist_ok=True)
                f.save("frontend/assets/news/" + filename) 
                
                
            editBlog(articleId,title,body,company,file)
            return redirect(url_for('blogOrArticlePage',articleId = articleId,page = page))
        ###DELETING THE ARTICLE!
        #Note it actually deletes it this time
        if request.method == "POST" and "deleteArticle" in request.form:
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            deleteBlog(articleId)
            addPopupMessage("Deleted blog/article successfully","good")
            return redirect(url_for('blog'))
        ###DELETING COMMENTS
        if request.method == "POST" and "deleteComment" in request.form:
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            author_id = str(request.form.get("author_id"))
            comment_id = str(request.form.get("comment_id"))
            deleteBlogComment(comment_id,author_id)
            addPopupMessage("Deleted comment successfully","good")
            return redirect(url_for('blogOrArticlePage',articleId = articleId,page = page))
        ###POSTING COMMENTS
        if request.method == "POST" and "postComment" in request.form: 
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            reply_body = str(request.form.get("body"))
            author_id = session["user_id"]
            post_id = addBlogComment(articleId,author_id,reply_body)
            newPage = getPagePostBlog(post_id,articleId)
            return redirect(url_for('blogOrArticlePage',articleId = articleId,page = newPage))
        
        ###EDITING YOUR COMMENTS
        if request.method == "POST" and "editComment" in request.form: 
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            commentID = str(request.form.get("comment_id"))
            body = str(request.form.get("body"))
            editBlogComment(commentID,body)
            return redirect(url_for('blogOrArticlePage',articleId = articleId,page = page))

        conn, cursor = get_db()
        query = """SELECT users.first_name, users.last_name, articles.title, articles.body, articles.company, articles.created, articles.image_url, articles.enable_comments,users.id as "user_id"
FROM articles
LEFT JOIN users ON users.id = articles.author_id
WHERE articles.id = ?;"""

        cursor.execute(query,(articleId,))
        
        news = cursor.fetchone()
        if not news:
            close_db()
            abort(404)
        cursor.execute(""" SELECT id, title, date, time, location, description, image FROM events ORDER BY date ASC""")
        columns = [d[0] for d in cursor.description]
        events_list = [dict(zip(columns, row)) for row in cursor.fetchall()]

        article = {
            "author" : ((news[0] or "") + " " + (news[1] or "")).strip() or "[deleted user]",
            "title" : news[2],
            "company" : news[4],
            "date" : news[5],
            "body" : news[3],
            "image_url" : news[6],
            "enable_comments" : news[7],
            "id" : articleId,
            "user_id": news[8],
        }
        comments = [

        ]
        pages = 0
        if news[7] == 1:
            query = """SELECT users.first_name,users.last_name,blog_comments.body,blog_comments.created_at,users.id,blog_comments.id,users.avatar,count(*) OVER() AS "full_count",blog_comments.deleted
FROM blog_comments
LEFT JOIN users ON blog_comments.author_id = users.id
WHERE blog_comments.article_id = ?
ORDER BY blog_comments.created_at ASC
LIMIT ? OFFSET ?;"""
            cursor.execute(query,(articleId,max_comments,(page-1)*max_comments,))
            
            totalComments = 0
            rows = cursor.fetchall()
        ## replycount = 0
            for i in rows:
                ##replycount = replycount + 1
                comments.append({
                    'author': {'username': ((i[0] or "") + " " + (i[1] or "")).strip() or "[deleted user]"},
                    'body': i[2],
                    'date': i[3],
                    'author_id':i[4],
                    'post_id':i[5],
                    'avatar' : i[6] or "assets/default_avatar.png",
                    'deleted' : i[8],
                })
                totalComments = i[7]
            print("THREADS:" ,totalComments)
            pages = math.ceil(totalComments/max_comments)

        close_db()
        


        
        return render_template("blog_page_or_article.html", page = page, article=article, events=events_list,comments = comments,pages = pages)
    # ---------------------
    def addBlogComment(articleID,authorID,body):
        conn, cursor = get_db()
        query = "INSERT INTO blog_comments (author_id,article_id,body) VALUES (?, ?, ?) RETURNING *"
        cursor.execute(query, (authorID,articleID,body))
        id = cursor.fetchone()
        conn.commit() 

        print(id[0])
        close_db()
        return id[0]
    
    def getPagePostBlog(comment_id,articleID):
        max_comments = 5
        conn, cursor = get_db()
        
        query = """SELECT blog_comments.id
        FROM blog_comments
        WHERE blog_comments.article_id = ?
        ORDER BY blog_comments.created_at ASC"""
        cursor.execute(query,(articleID,))
        id = cursor.fetchone()
        conn.commit() 

        rows = cursor.fetchall()
        replycount = 0
        page = 1
        for i in rows:
            replycount = replycount + 1
            print(comment_id,i[0])
            if str(i[0]) == str(comment_id):
                page = math.ceil((replycount + 1)/max_comments)
                print("Make")
                break
        ##ADd functionality to get the id of the recently created thread so one can immediately enter it upon creation.
        # cursor.execute("SELECT MAX(questions.id) from questions")
        print("PAGE:", page)
        close_db()
        return page
    def editBlogComment(commentID,body):
        conn, cursor = get_db()
        
        query = """
UPDATE blog_comments
SET body = ?
WHERE id = ?;
"""
        print("EDITING COMMENT ", body)
        cursor.execute(query, (body,commentID))
        conn.commit() 

        close_db()
    
    def deleteBlogComment(commentID,ownerID):
        status = 0
        if str(session["user_id"]) == str(ownerID):
            status = 1
        elif str(session["user_id"]) != str(ownerID) and session['role'] in ROLE_STAFF:
            status = 2
        
        if status > 0:
            conn, cursor = get_db()
            
            query = """
            UPDATE blog_comments
            SET body = ?, deleted = ?
            WHERE id = ?;
            """
            cursor.execute(query, ("",status,commentID,))
            conn.commit() 

            close_db()
            return True
        return False
        
    def editBlog(blogID,title,body,company,image_url):
        conn, cursor = get_db()
        
        query = """
UPDATE articles
SET title = ?, body = ?,company = ?,image_url = ?
WHERE id = ?;
"""
        print("EDITING COMMENT ", body)
        cursor.execute(query, (title,body,company,image_url,blogID,))
        conn.commit() 

        close_db()
        
    
    def deleteBlog(blogID):
        conn, cursor = get_db()
        query = """
        PRAGMA foreign_keys = ON;
        """
        cursor.execute(query)
        query = """
        DELETE FROM articles
        WHERE id = ?;
        """
        cursor.execute(query, (blogID,))
        conn.commit() 

        close_db()

    # ---------------------------------------------------------------------------------------------------


    @app.route("/create_account", methods = ["GET","POST"])
    @limiter.limit("5 per hour")
    def create_account(): 
        if 'user_id' in session:
            return redirect(url_for('homepage'))
        # conn, cursor = get_db() ##Commented out since its never used within the context apparently and its causing an error
        
        if request.method == "POST":
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            # static user elements.
            first_name = str(request.form.get("first_name")).strip()
            last_name = str(request.form.get("last_name")).strip()
            email = str(request.form.get("email", "")).strip()
            bio = str(request.form.get("bio"))
            
            # TODO - NOTE FOR NICK ADD THE LOGIC FOR A POSSIBLE AVATAR HERE
            # You do this by adding a image url variable
            # placeholder:
            avatar_url = "assets/default_avatar.png"

            
            # Passwords 
            entered_password = str(request.form.get("password"))
            check_password = str(request.form.get("check_password"))
            is_valid, errormessage = validate_credentials(email, entered_password, check_password, first_name, last_name)
            print(f"is_valid: {is_valid}, error: {errormessage}")  
            if is_valid == True:
                password_hash = bcrypt.hashpw(entered_password.encode('utf-8'), bcrypt.gensalt())
                                
                # do logic for checking before insert statements. 

                # EMAIL VERIFICATION 
                #taken from w3 schools + youtube . references TBA once completed
                
                # conn, cursor = get_db()
                token = secrets.token_urlsafe(32)
                session['pending_user'] = {
                    'first_name': first_name,
                    'last_name': last_name,
                    'email': email,
                    'password_hash': password_hash.decode('utf-8'), 
                    'avatar': avatar_url,
                    'token': token,
                    'expires_at': int(time.time()) + 3600  # 1 hour
                }
                
                try:
                    send_verification_email(email, token)
                except Exception:
                    session.pop('pending_user', None)
                    addPopupMessage("Failed to send verification email. Try again.","bad")
                    return render_template("create_account.html", error="Failed to send verification email. Try again.")
                
                    # return render_template("create_account.html", error=errormessage)
                return redirect(url_for('verify_pending'))
            # return render_template("create_account.html")
            addPopupMessage(errormessage,"bad")
            return render_template("create_account.html", error=errormessage)
        return render_template("create_account.html")

    # ---------------------------------------------------------------------------------------------------
    # add new placeholder

    @app.route("/about_team")
    def about_the_team(): 
        # static, leave as is (add more if eneded)
        return render_template("about_the_team.html")


    # ---------------------------------------------------------------------------------------------------


    @app.route("/contact_us")
    def contact_us():
        # static, add if needed 
        return render_template("contact.html")

    # ---------------------------------------------------------------------------------------------------


    @app.route("/programs")
    def programs():
        # Program cration template for admins only no? 
        # will be static and manually updated by admins but add functionality here
        return render_template("programs.html")

    # ---------------------------------------------------------------------------------------------------


    @app.route("/payment_page", methods=["GET"])
    def payment_page():
        module_id = request.args.get("module_id")

        return render_template(
            "payment_page.html",
            module_id=module_id,
            stripe_public_key=os.getenv("STRIPE_PUBLIC_KEY")
        )


    # TODO BEFORE THIS
    # EITHER IN MODULES PAGE OR OTHERWISE CHECK IF MODULE IS ALREADY PURCHASED BY USER
    # CHANGE THE WAY USERS SEE MODULES 
    # @Anthony-Dao @NickKaralis
    
    @app.route("/create-payment-intent", methods=["POST"])
    @limiter.limit("10 per minute")
    def create_payment_intent():

        conn, cursor = get_db()

        
        # Stripe requires this?
        delivery_type = "digital"
        address_type = "billing"

        first_name = request.form.get("first_name")
        last_name = request.form.get("last_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        address = request.form.get("address")
        module_id = request.form.get("module_id")
        
        # CHANGE BACK TO ABOVE WHEN ACTUALLY IMPLEMENTED THE MODULES PAGE
        # THIS IS SO YOU DONT GET ERRORS WHEN DOING PAYMENT PAGE>
        # module_id=19

        if not module_id:
            return jsonify({"error": "Missing module ID"}), 400

        cursor.execute("SELECT title, price FROM modules WHERE id = ?", (module_id,))
        module = cursor.fetchone()

        if not module:
            return jsonify({"error": "Module not found"}), 404

        module_title = module[0]
        module_price = module[1]

        
        # Stripe boiler plate 
        # TONOTE: Stripe requires payment intent --> payment --> order success and refund.
        try:
            price_cents = int(float(module_price) * 100)

            intent = stripe.PaymentIntent.create(
                amount=price_cents,currency="aud",
                automatic_payment_methods={"enabled": True},
                
                # might need session email to check*************8
                receipt_email=email,
                
                metadata={
                    "module_id": module_id,"module_title": module_title,"delivery_type": delivery_type,"address_type": address_type,"first_name": first_name,"last_name": last_name,"email": email,"phone": phone,"billing_address": address})

            session["delivery"] = {
                "type": delivery_type,"address_type": address_type,"address": address,"first_name": first_name,"last_name": last_name,"email": email,"phone": phone,"module_id": module_id }
            return jsonify({
                "client_secret": intent.client_secret})


        # thjrow erorr exception 
        except Exception as e:
            return jsonify({"error": str(e)}), 400




    # ---------------------------------------------------------------------------------------------------

    @app.route("/view_order", methods = ["GET", "POST"])
    def view_order(): 
        """ NOTE ADD HERE IF CONFIRM ORDER PAGE IS ANOTHER REDIRECT"""
        delivery = session.get('delivery')
        return render_template("view_order.html", delivery=delivery)
    @app.route("/payment_success", methods=["GET"])
    def payment_success():
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        payment_intent = request.args.get("payment_intent")
        redirect_status = request.args.get("redirect_status")
        
        if redirect_status != "succeeded":
            addPopupMessage("Failed to purchase module","bad")
            return render_template("payment_failed.html")
        
        delivery = session.get('delivery')
        if not delivery or not delivery.get('module_id'):
            return redirect(url_for('modules'))
        
        module_id = delivery['module_id']
        
        # verify payment with Stripe before granting access
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent)
            if intent.status != "succeeded":
                addPopupMessage("Failed to purchase module","bad")
                return render_template("payment_failed.html")
        except Exception:
            addPopupMessage("Failed to purchase module","bad")
            return render_template("payment_failed.html")
        
        # only purchase if not already owned
        if not isModulePurchased(module_id, session.get('user_id')):
            # purchaseModule(module_id, session.get('user_id'))
            try:
                purchaseModule(module_id, session.get('user_id'))
                addPopupMessage("Purchased module successfully","good")
            except Exception:
                addPopupMessage("Failed to purchase module","bad")
        
        session.pop('delivery', None)
        return redirect(url_for('yourModules'))
    # ---------------------------------------------------------------------------------------------------
    # NOTE: BUGFIX NO ROUTE FOR CREATE ARTICLE - im not using a function anymore
    # we are using a tab and form so this is like a tab in the html
    @app.route("/admin/create_news", methods=["GET", "POST"])
    def create_article(): 

        if 'user_id' not in session:
            return redirect(url_for('login'))
        conn, cursor = get_db()


        # THIS IS TEMPORARY DEPENDING ON WHO CAN CREATE ARTICLES -- and what the roles are going to be
        #            <!-- {% comment %} REFERENCES FOR THE JS {% endcomment %}
        # # {% comment %} ALSO referenced in api routing guys {% endcomment %}
        # #     {% comment %}     # template taken from: https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/files
        # #     # https://developer.mozilla.org/en-US/docs/Web/API/Document/querySelectorAll {% endcomment %}
        # #     {% comment %} https://developer.mozilla.org/en-US/docs/Web/API/Document/getElementById {% endcomment 
        if session['role'] not in ROLE_STAFF:
            addPopupMessage("You do not have permission to create an article.","bad")
            return redirect(url_for("homepage"))

        if request.method == "POST":
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            type = str(request.form.get("type_article"))
            print(type)
            
            
            # f = request.files['file']
            f = request.files.get("file")
            image = "NIL"

            if f and f.filename != "":
                error = validate_image_upload(f)
                if error:
                    close_db()
                    return render_template("create_news_article.html", error=error)

                filename = secure_filename(f.filename)
                image = "assets/news/" + filename

                print("FILENAME:", filename)
                Path("frontend/assets/news").mkdir(parents=True, exist_ok=True)
                f.save("frontend/assets/news/" + filename)
                
                
                
                
            title = request.form.get("title", "").strip()
            body = request.form.get("body", "").strip()
            company = request.form.get("company", "")
            author_id = session['user_id']

            # news
            if type == 'news_exclusive':
                cursor.execute(
                    "INSERT INTO news (title, body, author, company,image_url) VALUES (?, ?, ?, ?, ?)",
                    (title, body, author_id, company,image)
                )
                conn.commit()
                close_db()
                addPopupMessage("Created news successfully","good")
                return redirect(url_for('news'))
            # articles and blogs
            else: 
                comments = 0
                if type == 'blog':
                    comments = 1
                cursor.execute(
                    "INSERT INTO articles (title, body, author_id, company,image_url,enable_comments) VALUES (?, ?, ?, ?, ?,?)",
                    (title, body, author_id, company,image,comments)
                )
                conn.commit()
                close_db()
                addPopupMessage("Created blog/article successfully","good")
                return redirect(url_for('blog'))

            # conn.commit()
            # close_db()
            # return redirect(url_for('news'))

        close_db()
        return render_template("create_news_article.html")
    # ---------------------------------------------------------------------------------------------------


    # ATT DEVS: ------------------------------
    # as we add pages add the simmilar format here
    
    # -- ADMIN PAGE ----------------------------------------------
    # I did some js which well i suck at js but internet dosent
    # read over the html because references here. 
    # template taken from: https://developer.mozilla.org/en-US/docs/Web/API/HTMLInputElement/files
    # https://developer.mozilla.org/en-US/docs/Web/API/Document/querySelectorAll
    @app.route("/admin", methods=["GET", "POST"])
    def admin():
        if 'user_id' not in session or session.get('role') not in ROLE_STAFF:
            return redirect(url_for('homepage'))
        if session['role'] not in ROLE_STAFF:
            return redirect(url_for('homepage'))
        # succ and erorr are redundancy feel free to remove later.
        
        conn, cursor = get_db()
        success = None
        error = None
        active_tab = request.args.get("tab", "events")
        query = request.args.get("q", "").strip()
        users = []
        # DELETED ORIGINAL POST METHOD GETS AND SETS BECAUSE OF ROLE ADDITIONS.
        if request.method == "POST":
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            form_type = request.form.get("form_type")
            # role changing stuff here
            if form_type == "role":
            
                active_tab = "users"
                target_id = request.form.get("target_id")
                new_role = request.form.get("new_role")

                actor_role = get_user_role(cursor, session['user_id'])
                target_role = get_user_role(cursor, target_id)

                if str(target_id) == str(session['user_id']):
                    error = "You cannot change your own role."
                elif target_role is None:
                    error = "User not found."
                elif new_role not in ("admin", "regular"):
                    error = "Invalid role."
                elif not can_manage_user(actor_role, target_role):
                    error = "You do not have permission to change this user's role."
                else:
                    set_user_role(cursor, target_id, new_role)
                    conn.commit()
                    success = f"User #{target_id} is now '{new_role}'."
            elif form_type == "delete_user":
                active_tab = "users"
                target_id = request.form.get("target_id")

                actor_role = get_user_role(cursor, session['user_id'])
                target_role = get_user_role(cursor, target_id)

                if str(target_id) == str(session['user_id']):
                    error = "You cannot delete your own account."
                elif target_role is None:
                    error = "User not found."
                elif not can_manage_user(actor_role, target_role):
                    error = "You do not have permission to delete this user."
                else:
                    delete_user(cursor, target_id)
                    conn.commit()
                    success = f"User #{target_id} deleted."
            # Create event section
            elif form_type == "event":
                active_tab = "events"
                
                title = str(request.form.get("title","")).strip()
                date = str(request.form.get("date","")).strip()
                
                time = str(request.form.get("time", "")).strip()
                
                location = str(request.form.get("location", "")).strip()
                desc = str(request.form.get("desc","")).strip()
                # iomage upload saving - here and in backend funcs
                # image = save_event_image(request.files.get("image"))
                
                event_image = request.files.get("image")

                error = validate_image_upload(event_image)
                if error:
                    close_db()
                    return render_template("admin.html", success=success, error=error, active_tab=active_tab, query=query, users=users, current_user_id=session["user_id"] )

                image = save_event_image(event_image)
                
                is_valid, error_msg = validate_event(title, date)

                if is_valid:
                    event_id = insert_event(cursor, title, date, time, location, desc, image)
                    conn.commit()
                    success = f"Event '{title}' created (ID: {event_id})"
                else:
                    error = error_msg
            if success:
                addPopupMessage(success,"good")
            elif error:
                addPopupMessage(error,"bad")

        users = get_users(cursor, query)
            # print("USERS:", users) 

        close_db()
        # parse through if its valid, error messaages tabs active so that it maintains the website across reloads
        # pass through user sessions and user
        # it works by god i got no clue i prob will be debugging this later
        return render_template("admin.html", success=success, error=error, active_tab=active_tab, query=query, users=users, current_user_id=session['user_id'], current_user_role=session.get('role'))

    # ---------------------------------------------------------------------------------------------------


    @app.route("/search")
    def search():
        raw= request.args.get("q", "").strip()
        page = request.args.get("page", 1, type=int)
        PER = 10

        # tier labels shown in template badges + tabs
        TIERS = {
            'article':'Article',
            'news':'News',
            'module':'Module',
            'event':'Event',
            'forum':'Forum', }
        TIER_ORDER = ['article', 'news', 'module', 'event', 'forum']

        if not raw:
            return render_template("search_results.html",
                results=[], grouped={}, query='', page=1,
                pages=0, total=0, tiers=TIERS, tier_order=TIER_ORDER)

        q_tokens = tok(raw)
        conn, cursor = get_db()

        cursor.execute("""
            SELECT a.id, a.title, a.body AS snippet_src, a.image_url,
                u.first_name || ' ' || u.last_name AS meta
            FROM articles a LEFT JOIN users u ON a.author_id = u.id
            WHERE a.title IS NOT NULL ORDER BY a.created DESC LIMIT 60
        """)
        raw_articles = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT n.id, n.title, n.body AS snippet_src, n.image_url,
                u.first_name || ' ' || u.last_name AS meta
            FROM news n LEFT JOIN users u ON n.author = u.id
            ORDER BY n.created DESC LIMIT 60 """)
        raw_news = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT id, title, description AS snippet_src, image_url,
                CAST(price AS TEXT) AS meta
            FROM modules ORDER BY title ASC LIMIT 60""")
        raw_modules = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT id, title, description AS snippet_src, image AS image_url,
                location AS meta FROM events ORDER BY date ASC LIMIT 60""")
        raw_events = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

        cursor.execute("""
            SELECT q.id, q.title, q.body AS snippet_src, NULL AS image_url,
                u.first_name || ' ' || u.last_name AS meta FROM questions q LEFT JOIN users u ON q.author_id = u.id
            WHERE q.title IS NOT NULL AND q.deleted = 0 ORDER BY q.created_at DESC LIMIT 60 """)
        raw_forum = [dict(zip([d[0] for d in cursor.description], r)) for r in cursor.fetchall()]

        close_db()

        # -- URL builders per type
        def url_for_result(kind, row_id):
            if kind == 'article': return url_for('blogOrArticlePage', articleId=row_id)
            if kind == 'news': return url_for('newsArticle',newsId=row_id)
            if kind == 'module':return url_for('moduleView',module_id=row_id)
            if kind == 'event': return f"/index#event-{row_id}"   # adjust if you have an event detail page
            if kind == 'forum': return url_for('forumThread', threadID=row_id)

        def build(kind, rows, text_fields):
            ranked = rank(rows, q_tokens, text_fields)
            out = []
            for r in ranked:
                out.append({
                    'type': kind,
                    'tier_label': TIERS[kind],
                    'url': url_for_result(kind, r['id']),
                    'title': r.get('title') or '(untitled)',
                    'snippet': snippet(r.get('snippet_src') or '', q_tokens),
                    'meta': r.get('meta') or '',
                    'image_url':r.get('image_url') or '',
                })
            return out

        grouped = {
            'article': build('article', raw_articles, ['title','snippet_src']),
            'news': build('news', raw_news, ['title','snippet_src']),
            'module': build('module', raw_modules, ['title','snippet_src']),
            'event': build('event', raw_events, ['title','snippet_src','meta']),
            'forum': build('forum', raw_forum,['title','snippet_src']), }

        # interleave by tier priority: take 1 from each tier in order, repeat
        flat = []
        max_len = max((len(v) for v in grouped.values()), default=0)
        for i in range(max_len):
            for tier in TIER_ORDER:
                if i < len(grouped[tier]):
                    flat.append(grouped[tier][i])

        total = len(flat)
        pages = math.ceil(total / PER) if total else 0
        paged = flat[(page-1)*PER : page*PER]

        return render_template("search_results.html",
            results=paged, grouped=grouped, query=raw,
            page=page, pages=pages, total=total,
            tiers=TIERS, tier_order=TIER_ORDER)
        
    # ---------------------------------------------------------------------------------------------------

    # CPPIED TEMPLATE FROM YOUTUBE, STACK and W3 more tba later for refs
    @app.route("/verify_pending")
    def verify_pending():
        if 'pending_user' not in session:
            return redirect(url_for('create_account'))
        email = session['pending_user']['email']
        return render_template("verify_pending.html", email=email)
    
    
    
    # ---------------------------------------------------------------------------------------------------

    @app.route("/verify_email")
    def verify_email():
        token = request.args.get("token", "")
        pending = session.get('pending_user')

        if not pending:
            return render_template("verify_result.html", success=False,  message="Session expired or link already used. Please register again.")
        if pending['token'] != token:
            return render_template("verify_result.html", success=False, message="Invalid verification link.")
        
        
        if int(time.time()) > pending['expires_at']:
            session.pop('pending_user', None)
            return render_template("verify_result.html", success=False,message="Link expired. Please register again.")

        conn, cursor = get_db()
        try:
            ### You forgot to remove bio from email verification
            cursor.execute( "INSERT INTO Users (first_name, last_name, email, password_hash, avatar) VALUES (?, ?, ?, ?, ?)", (pending['first_name'], pending['last_name'], pending['email'],pending['password_hash'], pending['avatar']))
            conn.commit()
        except Exception:
            print(traceback.format_exc())
            close_db()
            return render_template("verify_result.html", success=False, message="Account could not be created. Email may already be registered or an unknown error has occurred.")

        session.pop('pending_user', None)
        close_db()
        return render_template("verify_result.html", success=True, message="Success! Press Sign In to get started.")
    
    
    
    # ---------------------------------------------------------------------------------------------------
    # This is not under the admin function
    # i have three tabs in here and yes i could insert this within it but
    # there are issues with organissation and passing values i couldnt figure out
    # TODO later is to pass thisinto one function
    
    # also technically the page within the page is admin/user or admin/create evemt
    @app.route("/admin/users", methods=["GET", "POST"])
    def admin_users():
        if 'user_id' not in session or session.get('role') not in ROLE_STAFF:
            return redirect(url_for('homepage'))

        conn, cursor = get_db()
        query = request.args.get("q", "").strip()
        success = None
        error = None

        if request.method == "POST":
            if request.form.get('website'):
                return redirect(url_for('homepage'))
            target_id = request.form.get("target_id")
            new_role = request.form.get("new_role")
            current_user_id = session['user_id']

            actor_role = get_user_role(cursor, current_user_id)
            target_role = get_user_role(cursor, target_id)

            # DELETE ACCOUNT
            if request.form.get("action") == "delete_user":
                if str(target_id) == str(current_user_id):
                    error = "You cannot delete your own account."
                elif target_role is None:
                    error = "User not found."
                elif not can_manage_user(actor_role, target_role):
                    error = "You do not have permission to delete this user."
                else:
                    delete_user(cursor, target_id)
                    conn.commit()
                    success = f"User #{target_id} deleted."
            # CHANGE ROLE
            elif str(target_id) == str(current_user_id):
                error = "roles equal to your own "
            elif target_role is None:
                error = "User not found."
            elif new_role not in ("admin", "regular"):
                error = "Invalid role."
            elif not can_manage_user(actor_role, target_role):
                error = "You do not have permission to change this user's role."
            else:
                set_user_role(cursor, target_id, new_role)
                conn.commit()
                success = f"User #{target_id} is now '{new_role}'."
            if success:
                addPopupMessage(success,"good")
            elif error:
                addPopupMessage(error,"bad")

        users = get_users(cursor, query)
        close_db()
        
        return render_template("admin_users.html", users=users, query=query, success=success, error=error, current_user_id=session['user_id'])
    
    
    # THE DREADED MODULES :(((((((
 # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------
    # ---------------------------------------------------------------------------------------------------


    UPLOAD_FOLDER = os.path.join("frontend", "assets", "module_pdfs")
    ALLOWED_EXTENSIONS = {"pdf"}
    MAX_PARTS = 20
    SECTION_UPLOAD_FOLDER = os.path.join("frontend", "assets", "module_sections")

    def allowed_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


    def admin_required(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if session.get("role") not in ROLE_STAFF:
                return redirect(url_for("homepage"))
            return f(*args, **kwargs)
        return decorated



    def register_module_admin_routes(app):

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        # -- Page route ------------------------------------------------------------
        @app.route("/admin/create_module", methods=["GET"])
        @admin_required
        def create_module_page():
            return render_template("create_module.html")


        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        # -------------------------------------------------------------------------
        
        # CREATE MODULE 
        @app.route("/api/admin/modules", methods=["POST"])
        @admin_required
        def api_create_module():
            # print(request)
            # print(request.files)
            # data        = request.get_json()
            title = request.form.get("title")
            description = request.form.get("description")
            price_cents = int(request.form.get("price_cents", 0))
            print(title)
            print(description)
            print(price_cents)
            f = request.files.get("image_url")
            image = "assets/modules/foodcomputingacademy.png"
            
            
            if f and f.filename != "":
                error = validate_image_upload(f)
                if error:
                    return jsonify({"error": error}), 400

                filename = secure_filename(f.filename)
                image = "assets/modules/" + filename

                print("FILENAME:", filename)
                Path("frontend/assets/modules").mkdir(parents=True, exist_ok=True)
                f.save("frontend/assets/modules/" + filename)
                
                


            if not title:
                return jsonify({"error": "Title is required"}), 400

            conn, cursor = get_db()
            cursor.execute(
                "INSERT INTO modules (title, description, price,image_url) VALUES (?, ?, ?,?)",
                (title, description, price_cents,image),
            )
            conn.commit()
            module_id = cursor.lastrowid
            close_db()
            return jsonify({"module_id": module_id}), 201

        # Add part to module (title + optional PDF) 
        # WIll add the body section later
        # @Anthony-Dao
        # POST /url/admin/modules/<module_id>/parts
        # Form data: title, part_number, has_quiz, pdf_file (optional), and will have body next commit
        # Returns integer part id.
        # -------------------------------------------------------------------------
        @app.route("/api/admin/modules/<int:module_id>/parts", methods=["POST"])
        @admin_required
        def api_add_part(module_id):
            title = (request.form.get("title") or "").strip()
            part_number = request.form.get("part_number", type=int)
            # check if quiz is added after part
            # less work than making na option each time for a quiz just attach to a part or end of section to be added later
            has_quiz = 1 if request.form.get("has_quiz") == "1" else 0

            body = (request.form.get("body") or "")
            youtube_url = (request.form.get("youtube_url") or "")
            
            file= request.files.get("pdf_file")

            if not title:
                return jsonify({"error": "Part title is required"}), 400
            if not part_number or not (1 <= part_number <= MAX_PARTS):
                return jsonify({"error": f"part_number must be between 1 and {MAX_PARTS}"}), 400

            pdf_path = None

            if file and file.filename != "":
                error = validate_pdf_upload(file)
                if error:
                    return jsonify({"error": error}), 400

                filename = secure_filename(file.filename)
                filename = f"module{module_id}_part{part_number}_{filename}"
                full_path = os.path.join(UPLOAD_FOLDER, filename)

                file.save(full_path)
                pdf_path = f"assets/module_pdfs/{filename}"

            conn, cursor = get_db()

            cursor.execute("SELECT id FROM modules WHERE id = ?", (module_id,))
            if not cursor.fetchone():
                close_db()
                return jsonify({"error": "Module not found"}), 404

            cursor.execute(
                "SELECT id FROM module_parts WHERE module_id = ? AND part_number = ?",
                (module_id, part_number),)
           
           
            if cursor.fetchone():
                close_db()
                return jsonify({"error": f"Part {part_number} already exists for this module"}), 409

            cursor.execute(
                """INSERT INTO module_parts (module_id, part_number, title, pdf_path, has_quiz, body, youtube_url) VALUES (?, ?, ?, ?, ?,?,?) RETURNING * """,
                (module_id, part_number, title, pdf_path, has_quiz,body,youtube_url),)
            
            part_id = cursor.fetchone()[0]
            conn.commit()
            print(part_id)
            close_db()
            return jsonify({"part_id": part_id}), 201



        # -------------------------------------------------------------------------
        # CREATE QUIZ
        # RETURNS QUIZ ID AS AN INTEGER --> Will convert to big int later
        @app.route("/api/admin/quizzes", methods=["POST"])
        @admin_required
        def api_create_quiz():
            data = request.get_json()
            part_id = data.get("part_id")
            module_id = data.get("module_id")
            title = (data.get("title") or "").strip()
            is_final_exam = int(data.get("is_final_exam", 0))
            pass_percent  = int(data.get("pass_percent", 80))
            # if not part_id:
            #     return jsonify({"error": "part id required"}), 400
            if not module_id:
                return jsonify({"error": "module id required"}), 400
            if not title :
                return jsonify({"error": "Quiz title is required"}), 400
            if is_final_exam and not module_id:
                
                return jsonify({"error": "module_id required for final exam"}), 400
            if not is_final_exam and not part_id:
                
                return jsonify({"error": "part_id required for part quiz"}), 400
            # SET FINAL EXAM PERCENTAGE DEBUGGER DONT ALLOW NEG or 0 . CHANGE TO DEFAULT 50 for prod
            if not (0 <= pass_percent <= 100):
                return jsonify({"error": "pass_percent must be 0-100"}), 400

            conn, cursor = get_db()
            cursor.execute(
                """INSERT INTO module_quizzes (module_id, part_id, title, is_final_exam, pass_percent)
                VALUES (?, ?, ?, ?, ?)""",
                (module_id, part_id, title, is_final_exam, pass_percent),)
            conn.commit()
            quiz_id = cursor.lastrowid
            
            
            close_db()
            return jsonify({"quiz_id": quiz_id}), 201

        # -------------------------------------------------------------------------
        # POST method for questions and answers for quizzes
        # returns question id for db. 
        # will add body soon
        
        
        # NOTES:::::
        # Note: body of the quiz is as follows
        # Body = Object ( "question_text" (string) "question_type": "multiple_choice"|"true_false",
        # "order_num": int,
        # "answers": [{ "text": str, "is_correct": bool }, ...] }
        # Returns: { "question_id": int }
        # -------------------------------------------------------------------------
        @app.route("/api/admin/quizzes/<int:quiz_id>/questions", methods=["POST"])
        @admin_required
        def api_add_question(quiz_id):
            # data = request.get_json()
            
            question_text = request.form.get("question_text") # (data.get("question_text") or "").strip()
            question_type = request.form.get("question_type") # data.get("question_type", "multiple_choice")
            # question_image = data.get("question_image")
            order_num = request.form.get("order_num") # int(data.get("order_num", 0))
            # answers = request.form.get("answers").get_json() # data.get("answers", [])
            # print(answers)
            # print(answers[0])
            # print(answers[0]['text'])
            # print(answers[0]['is_correct'])
            f = request.files.get("question_image")
            image = "NIL"

            if f and f.filename != "":
                error = validate_image_upload(f)
                if error:
                    return jsonify({"error": error}), 400

                filename = secure_filename(f.filename)
                image = "assets/modules/" + filename

                print("FILENAME:", filename)
                Path("frontend/assets/modules").mkdir(parents=True, exist_ok=True)
                f.save("frontend/assets/modules/" + filename)

            if not question_text:
                return jsonify({"error": "question_text is required"}), 400
            
            if question_type not in ("multiple_choice", "true_false"):
                return jsonify({"error": "question_type must be multiple_choice or true_false"}), 400
            # if not answers:
                
            #     return jsonify({"error": "At least one answer is required"}), 400
            # if question_type == "true_false" and len(answers) != 2:
            #     return jsonify({"error": "true_false questions must have exactly 2 answers"}), 400

            # correct_count = sum(1 for a in answers if a.get("is_correct"))
            # if correct_count != 1:
            #     return jsonify({"error": "Exactly one answer must be marked correct"}), 400

            conn, cursor = get_db()
            cursor.execute("SELECT id FROM module_quizzes WHERE id = ?", (quiz_id,))
            if not cursor.fetchone():
                close_db()
                return jsonify({"error": "Quiz not found"}), 404

            cursor.execute(
                """INSERT INTO module_questions (quiz_id, question_text, question_type, order_num,image_url)
                VALUES (?, ?, ?, ?,?)""",
                (quiz_id, question_text, question_type, order_num,image),
            )
            question_id = cursor.lastrowid

            # for ans in answers:
            #     cursor.execute(
            #         """INSERT INTO module_answers (question_id, answer_text, is_correct)
            #         VALUES (?, ?, ?)""",
            #         (question_id, (ans.get("text") or "").strip(), 1 if ans.get("is_correct") else 0),)

            conn.commit()
            close_db()
            return jsonify({"question_id": question_id}), 201
        @app.route("/api/admin/quizzes/<int:quiz_id>/questions/<int:question_id>", methods=["POST"])
        @admin_required
        def api_add_answer(quiz_id,question_id):
            answer_text = request.form.get("answer_text") # (data.get("question_text") or "").strip()
            is_correct = request.form.get("is_correct").strip().lower() == "true" # data.get("question_type", "multiple_choice")
            print(answer_text)
            print(is_correct)
            conn, cursor = get_db()
            cursor.execute("SELECT id FROM module_questions WHERE id = ?", (question_id,))
            if not cursor.fetchone():
                close_db()
                return jsonify({"error": "Question not found"}), 404

            cursor.execute(
                """INSERT INTO module_answers (question_id,answer_text,is_correct)
                VALUES (?, ?, ?)""",
                (question_id,answer_text,is_correct,),
            )
            answer_id = cursor.lastrowid

            # for ans in answers:
            #     cursor.execute(
            #         """INSERT INTO module_answers (question_id, answer_text, is_correct)
            #         VALUES (?, ?, ?)""",
            #         (question_id, (ans.get("text") or "").strip(), 1 if ans.get("is_correct") else 0),)

            conn.commit()
            close_db()
            return jsonify({"answer_id": answer_id}), 201
        
        # This is redundant because anthony u rewrote it? with complete
        
        # @app.route("/modules/module/<module_id>/finish", methods=["GET"])
        # def moduleFinish(module_id):
        #     if 'user_id' not in session:
        #         return redirect(url_for('login'))
        #     if not isModulePurchased(module_id, session.get('user_id')):
        #         return redirect(url_for('moduleView', module_id=module_id))
            
        #     conn, cursor = get_db()
        #     progress = getProgress(cursor, session.get('user_id'), module_id)
            
        #     query = """SELECT modules.title FROM modules WHERE modules.id = ?"""
        #     cursor.execute(query, (module_id,))
        #     module = cursor.fetchone()
        #     close_db()
            
        #     return render_template("module_finish.html", module_id=module_id,module_title=module[0],progress=progress)
                
        # -------------------------------------------------------------------------------------------------------------
        # HELPERS
        @app.route("/api/admin/modules/<int:module_id>/parts", methods=["GET"])
        @admin_required
        def api_get_parts(module_id):
            conn, cursor = get_db()
            cursor.execute(
                """SELECT id, part_number, title, pdf_path, has_quiz
                FROM module_parts WHERE module_id = ?
                ORDER BY part_number ASC""",
                (module_id,),)
            rows = cursor.fetchall()
            close_db()
            parts = [{"id": r[0], "part_number": r[1], "title": r[2], "pdf_path": r[3], "has_quiz": r[4]} for r in rows]
            return jsonify({"parts": parts}), 200
            
            
            
        @app.route("/api/admin/parts/<int:part_id>/sections", methods=["GET"])
        @admin_required
        def api_get_sections(part_id):
            conn, cursor = get_db()
            cursor.execute(
                "SELECT id, section_type, content, order_num "
                "FROM module_part_sections WHERE part_id = ? ORDER BY order_num ASC",
                (part_id,)
            )
            cols = [d[0] for d in cursor.description]
            sections = [dict(zip(cols, r)) for r in cursor.fetchall()]
            close_db()
            return jsonify({"sections": sections}), 200

        @app.route("/api/admin/parts/<int:part_id>/sections", methods=["POST"])
        @admin_required
        def api_add_section(part_id):
            section_type = (request.form.get("section_type") or "").strip().lower()
            content = (request.form.get("content") or "").strip()
            order_num = request.form.get("order_num", 0, type=int)

            if section_type not in ("text", "image", "youtube", "pdf"):
                return jsonify({"error": "section_type must be text, image, youtube, or pdf"}), 400

            conn, cursor = get_db()

            cursor.execute("SELECT id FROM module_parts WHERE id = ?", (part_id,))
            if not cursor.fetchone():
                close_db()
                return jsonify({"error": "Part not found"}), 404

            if section_type == "text":
                if not content:
                    close_db()
                    return jsonify({"error": "Text section cannot be empty"}), 400

            elif section_type == "youtube":
                if not content:
                    close_db()
                    return jsonify({"error": "YouTube URL is required"}), 400

            elif section_type == "image":
                f = request.files.get("file")

                if not f or not f.filename:
                    close_db()
                    return jsonify({"error": "Image file required"}), 400

                err = validate_image_upload(f)
                if err:
                    close_db()
                    return jsonify({"error": err}), 400

                filename = secure_filename(f.filename)
                filename = f"{uuid.uuid4().hex}_{filename}"

                image_upload_dir = Path(app.static_folder) / "assets" / "modules"
                image_upload_dir.mkdir(parents=True, exist_ok=True)

                save_path = image_upload_dir / filename
                f.save(save_path)

                content = "assets/modules/" + filename

                print("SAVED MODULE PART IMAGE TO:", save_path.resolve())
                print("DB CONTENT:", content)
            elif section_type == "pdf":
                f = request.files.get("file")

                if not f or not f.filename:
                    close_db()
                    return jsonify({"error": "PDF file required"}), 400

                err = validate_pdf_upload(f)
                if err:
                    close_db()
                    return jsonify({"error": err}), 400

                filename = secure_filename(f.filename)
                filename = f"{uuid.uuid4().hex}_{filename}"

                Path("frontend/assets/module_pdfs").mkdir(parents=True, exist_ok=True)
                f.save("frontend/assets/module_pdfs/" + filename)

                content = "assets/module_pdfs/" + filename

            cursor.execute(
                """
                INSERT INTO module_part_sections (part_id, section_type, content, order_num)
                VALUES (?, ?, ?, ?)
                """,
                (part_id, section_type, content, order_num)
            )

            conn.commit()
            section_id = cursor.lastrowid
            close_db()

            return jsonify({
                "section_id": section_id,
                "section_type": section_type,
                "content": content,
                "order_num": order_num
            }), 201
        @app.route("/api/admin/sections/<int:section_id>", methods=["PUT"])
        @admin_required
        def api_update_section(section_id):
            data      = request.get_json(silent=True) or {}
            content   = data.get("content")
            order_num = data.get("order_num")
            conn, cursor = get_db()
            if content is not None:
                cursor.execute("UPDATE module_part_sections SET content = ? WHERE id = ?", (content, section_id))
            if order_num is not None:
                cursor.execute("UPDATE module_part_sections SET order_num = ? WHERE id = ?", (order_num, section_id))
            conn.commit()
            close_db()
            return jsonify({"updated": section_id}), 200

        @app.route("/api/admin/sections/<int:section_id>", methods=["DELETE"])
        @admin_required
        def api_delete_section(section_id):
            conn, cursor = get_db()
            cursor.execute("DELETE FROM module_part_sections WHERE id = ?", (section_id,))
            conn.commit()
            close_db()
            return jsonify({"deleted": section_id}), 200

        @app.route("/api/admin/sections/reorder", methods=["POST"])
        @admin_required
        def api_reorder_sections():
            items = request.get_json(silent=True) or []
            conn, cursor = get_db()
            for item in items:
                cursor.execute(
                    "UPDATE module_part_sections SET order_num = ? WHERE id = ?",
                    (item["order_num"], item["id"])
                )
            conn.commit()
            close_db()
            return jsonify({"reordered": True}), 200
        
            
    register_module_admin_routes(app)
