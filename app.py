from flask import Flask, flash, redirect, render_template, request, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3


app = Flask(__name__)

app.secret_key = "beebs"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":

        username = request.form.get("username")
        username = username.strip()
        password = request.form.get("password")
        confirm = request.form.get("confirm")

        if not username:
            return render_template("register.html", error="Missing username")
        
        elif not password or not confirm:
            return render_template("register.html", error="Missing password")
        
        elif password != confirm:
            return render_template("register.html", error="Passwords must match")
        
        with sqlite3.connect("choretracker.db") as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # check exists
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()
            if user:
                return render_template("register.html", error="Username already exists")
        
            # insert if needed
            cursor.execute("INSERT INTO users (username, password_hash) VALUES(?, ?)",
                   (username, generate_password_hash(password)))

            new_id = cursor.lastrowid
            session["user_id"] = new_id

        flash("Registered")
        return redirect("/")

    else:
        return render_template("register.html")        


if __name__ == "__main__":
    app.run(debug=True)