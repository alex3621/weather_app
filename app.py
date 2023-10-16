import os
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from helpers import apology, login_required, lookup, usd
import requests
from dotenv import load_dotenv
from sqlalchemy import JSON
import requests

load_dotenv()
API_KEY = os.environ.get("API_KEY")
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# adding database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.sqlite3"

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure db for sqlalchemy
db = SQLAlchemy(app)

def get_weather_data(city_name, api_key):
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city_name,
        "appid": api_key,
    }
    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 200:
            weather_data = response.json()
            return weather_data
        else:
            return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


class users(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    username = db.Column("username", db.String(100), nullable=False)
    hash = db.Column("hash", db.String(200), nullable=False)
    cities = db.Column("cities", db.PickleType, nullable=True)

    def __init__(self, username, hash):
        self.username = username
        self.hash = hash
        
class cities(db.Model):
    id = db.Column("id", db.Integer, primary_key=True)
    city_name = db.Column("city_name", db.String(255), nullable=False)
    user_id = db.Column("user_id", db.Integer, db.ForeignKey("users.id"), nullable=False)

    def __init__(self, city_name, user_id):
        self.city_name = city_name
        self.user_id = user_id


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0")


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        else:
            form_username = request.form.get("username")
            form_password = request.form.get("password")
            rows = users.query.filter_by(username=form_username).first()
            # print(check_password_hash(rows[0]["hash"], password))

        # Ensure username exists and password is correct
        if not rows or not check_password_hash(rows.hash, form_password):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows.id

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    else:
        form_username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        if not form_username or not password or not confirmation:
            return apology("must fill out form", 400)

        username_check = users.query.filter_by(username=form_username).first()

        if confirmation != password:
            return apology("confirmation not correct")
        elif username_check:
            return apology("username already taken")
        else:
            password = generate_password_hash(
                password, method="pbkdf2:sha1", salt_length=8
            )
            stocks = []
            user = users(form_username, password, stocks)
            db.session.add(user)
            db.session.commit()
            flash("successful registration")
            return redirect("/")


@app.route("/add_city", methods=["GET", "POST"])
@login_required
def add_city():
    if request.method == "GET":
        return render_template("add_city.html")

    if request.method == "POST":
        user_id = session["user_id"]
        user = users.query.filter_by(id=user_id).first()
        city_name = request.form.get("city_name")

        if city_name:
            if "cities" not in user:
                user.cities = [city_name]
            else:
                user.cities.append(city_name)

            db.session.commit()
            flash("City added to your profile")
            return redirect("/")

        else:
            flash("Please enter a city name")
            return redirect("/add_city")


@app.route("/")
@login_required
def index():
    user_id = session["user_id"]
    user = users.query.filter_by(id=user_id).first()
    user_cities = user.cities if "cities" in user else []

    result = []

    for city_name in user_cities:
        weather_data = get_weather_data(city_name, API_KEY) 
        if weather_data:
            result.append(weather_data)

    return render_template("index.html", result=result, user_cities=user_cities)

