from flask import Flask, flash, redirect, render_template, request, session, url_for, abort, g
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3


app = Flask(__name__)

app.secret_key = "beebs"

def get_db_connection():
    conn = sqlite3.connect("choretracker.db")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_current_user():
    if hasattr(g, "current_user"):
        return g.current_user

    user_id = session.get("user_id")
    if not user_id:
        g.current_user = None
        return None

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        g.current_user = cursor.fetchone()
        return g.current_user

@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}

@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403

@app.route("/")
def index():
    user = get_current_user()

    if not user:
        return redirect(url_for("login"))

    if user["role"] == "parent":
        return redirect(url_for("parents"))

    return redirect(url_for("kids"))

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not username:
            return render_template("register.html", error="Missing username")
        
        elif not password or not confirm:
            return render_template("register.html", error="Missing password")
        
        elif password != confirm:
            return render_template("register.html", error="Passwords must match")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # check exists
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user:
                return render_template("register.html", error="Username already exists")
        
            # insert if needed
            cursor.execute("INSERT INTO users (username, password_hash, role) VALUES(?, ?, ?)",
                   (username, generate_password_hash(password), 'parent'))

            new_id = cursor.lastrowid
            session["user_id"] = new_id

        flash("Registered")
        return redirect(url_for("index"))

    else:
        return render_template("register.html")        

@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        session.clear()

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password")

        if not username:
            return render_template("login.html", error="Missing username")
        
        if not password:
            return render_template("login.html", error="Missing password")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # query database for username
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if not user or not check_password_hash(user["password_hash"],password):
                return render_template("login.html", error="Invalid username and/or password")

            session["user_id"] = user["id"]

        flash("Logged in")
        return redirect(url_for("index"))

    return render_template("login.html")
    

@app.route("/create-kid", methods=["GET","POST"])
def create_kid():

    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))

    if parent["role"] != "parent":
        abort(403)

    if request.method == "POST":

        username = (request.form.get("username") or "").strip()
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not username:
            return render_template("create-kid.html", error="Missing username")
        
        elif not password or not confirm:
            return render_template("create-kid.html", error="Missing password")
        
        elif password != confirm:
            return render_template("create-kid.html", error="Passwords must match")
        
        with get_db_connection() as conn:
            cursor = conn.cursor()

            # check exists
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            existing_user = cursor.fetchone()
            if existing_user:
                return render_template("create-kid.html", error="Username already exists")
        
            # insert if needed
            cursor.execute("INSERT INTO users (username, password_hash, role, parent_id) VALUES(?, ?, ?, ?)",
                   (username, generate_password_hash(password), 'kid', parent["id"]))

        flash("Kid created")
        return redirect(url_for("create_kid"))

    return render_template("create-kid.html") 


@app.route("/kids")
def kids():

    kid = get_current_user()

    if not kid:
        return redirect(url_for("login"))

    if kid["role"] != "kid":
        abort(403)
    
    return render_template("kids.html", kid=kid)


@app.route("/parents")
def parents():

    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))

    if parent["role"] != "parent":
        abort(403)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # get kid list
        cursor.execute("SELECT id, username FROM users WHERE role = 'kid' and parent_id = ?", (parent["id"],))
        kids = cursor.fetchall()

    return render_template("parents.html", parent=parent, kids=kids)


@app.route("/logout")
def logout():

    session.clear()
    flash("Logged out")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True)