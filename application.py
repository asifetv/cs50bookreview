import os
import requests

import flask_login
from flask import Flask, render_template, request, session, flash
from flask_session import Session

from sqlalchemy import create_engine, Integer, String
from sqlalchemy.orm import scoped_session, sessionmaker
from passlib.hash import sha256_crypt


app = Flask(__name__)

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))

#configure login manager
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

class User(flask_login.UserMixin):
    pass

@login_manager.user_loader
def user_loader(username):
    if db.execute("SELECT * FROM usertable WHERE username = :username", \
{"username": username}).rowcount == 0:
        return 
    user = User()
    user.id = username
    return user


@login_manager.unauthorized_handler
def unauthorized_handler():
    return Response('<Sorry, Please login before you can access>', 401, {'WWW-Authenticate':'Basic realm="Login Required"'})

def setUpTables ():
    #setup database
    #db.execute ('CREATE TABLE IF NOT EXISTS "usertable" ( '
    #            'username VARCHAR(100) NOT NULL,'
    #            'pwdhash VARCHAR(100) NOT NULL,'
    #            'firstname VARCHAR(100) NOT NULL,'
    #            'lastname VARCHAR(100) NOT NULL,'
    #            'email VARCHAR(120) NOT NULL UNIQUE,'
    #            'PRIMARY KEY(username));')
    try:
        db.execute ("CREATE TABLE IF NOT EXISTS usertable (username VARCHAR(100) PRIMARY KEY UNIQUE, pwdhash VARCHAR(100) NOT NULL, firstname VARCHAR(100) NOT NULL,lastname VARCHAR(100) NOT NULL,email VARCHAR(120) NOT NULL)")
        db.execute ("CREATE TABLE IF NOT EXISTS reviewtable (username VARCHAR(100), isbn VARCHAR (100), ratings SMALLINT, review VARCHAR(1024), unique(username, isbn))")
    except:
        print("I can't create the database")
    db.commit ()
    
@app.route("/")
def index():
    setUpTables ()
    return render_template("index.html")   
    #res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "cwBmn0qQoZYskh4lrhpIw", "isbns": "9781632168146"})
    #return res.json()

@app.route("/userreview/", methods=["POST"])
@flask_login.login_required
def userreview ():
    isbn = request.args.get("isbn")
    rating = request.form.get("UserRating")
    review = request.form.get("UserReviewTextArea")
    if db.execute ("SELECT * FROM reviewtable WHERE isbn=:isbn AND username = :username", {"isbn":isbn, "username":flask_login.current_user.id}).rowcount == 0:
        db.execute("INSERT INTO reviewtable (isbn, username, ratings, review) VALUES (:isbn, :username, :ratings, :review)", {"isbn": isbn, "username":flask_login.current_user.id, "ratings": rating, "review": review})
        db.commit()
    else:
        flash("Review already exists")
    print (f"userreview: { review } userrating: { rating }")
    return render_template("review.html", isbn=isbn)
    
    
@app.route("/bookreview/", methods=["GET", "POST"])
@flask_login.login_required
def bookreview():
    isbn = request.args.get("isbn")
    print(isbn)
    book = db.execute ("SELECT * FROM books WHERE isbn = :isbn", {"isbn":isbn}).fetchall()
    if len(book) == 1:
        data_object={}
        data_object["isbn"] = book[0].isbn
        data_object["author"]=book[0].author
        data_object["title"]=book[0].title
        
        res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "cwBmn0qQoZYskh4lrhpIw", "isbns": "9781632168146"})
        if res.status_code != 200:
            flash("Unable to find data from good reads")
        else :
            goodread_data = res.json()
            data_object["average_rating"]=goodread_data["books"][0]["average_rating"]
            data_object["ratings_count"]=goodread_data["books"][0]["ratings_count"]
            print(f"Username is { flask_login.current_user.id }")
            userfeedback = db.execute("SELECT ratings, review FROM reviewtable WHERE username = :username and isbn = :isbn", {"username":flask_login.current_user.id, "isbn":isbn }).fetchall()
            if (userfeedback):
                print(userfeedback[0], len(userfeedback))
            if len(userfeedback) > 1:
                return render_template("error.html", message="review Table messed up")
            elif len(userfeedback) == 1:
                data_object["userrating"]=userfeedback[0].ratings
                data_object["userreview"]=userfeedback[0].review
            else:
                data_object["userrating"]=0
                data_object["userreview"]=""
            return render_template("book.html", book=data_object)
    else:
        flash("Cpnflicting ISBN")
        return render_template("error.html", message="Bad")


@app.route("/review", methods=["POST", "GET"])
@flask_login.login_required
def review():
    """review book """
    if request.method == "GET":
        return render_template("review.html", books={})
    elif request.method == "POST":
        bookid = request.form.get("bookid")
        books = db.execute("SELECT * FROM books WHERE isbn ~* :isbn OR title ~* :title OR author ~* :author", {"isbn": bookid, "title": bookid, "author": bookid}).fetchall()

        for book in books:
            print(book.title)
        return render_template("review.html", books=books)

@app.route("/login", methods=["POST"])
def login():
    """ Login to the application """
    username = request.form.get("usernamelogin")
    
    if db.execute("SELECT * FROM usertable WHERE username = :username", \
{"username": username}).rowcount == 0:
            flash("Username {username} not found")
            return render_template("index.html")
    else:
        passwdhash = db.execute("SELECT pwdhash FROM usertable WHERE username = :username", {"username": username}).fetchall()[0].pwdhash
        #print (request.form.get("passwordlogin"))
        if sha256_crypt.verify(request.form.get("passwordlogin"),passwdhash)== False:
            flash ("Incorrect password")
            return render_template("index.html")
        else:
            user = User()
            user.id = username
            flask_login.login_user(user)
            return render_template("review.html", message="Successfully logged in")

@app.route("/logout", methods=["POST"])
@flask_login.login_required
def logout ():
    flask_login.logout_user()
    return render_template("index.html")


@app.route("/signup", methods=["POST", "GET"])
def signup():
    """ Signup for the application """
    if request.method == "GET":
        print("Inside the signup function")
        return render_template("signup.html")
    elif request.method == "POST":
        username = request.form.get("username")
        pwdhash = sha256_crypt.encrypt(request.form.get("password"))
        firstname = request.form.get("firstname")
        lastname = request.form.get("lastname")
        email = request.form.get("emailid")
        print(username, pwdhash, firstname, lastname, email)
        #print(username, password, firstname, lastname)
        if db.execute("SELECT * FROM usertable WHERE username = :username", {"username": username}).rowcount > 0:
            flash("That username is already taken")
            return render_template("signup.html") 
        else:
            db.execute("INSERT into usertable (username, pwdhash, firstname, lastname, email) VALUES (:username, :pwdhash, :firstname, :lastname, :email)",
                       {"username": username, "pwdhash": pwdhash, "firstname": firstname, "lastname": lastname, "email": email})
            db.commit()
            return render_template("success.html", message="Registered user { username }")
