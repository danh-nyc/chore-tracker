from flask import Flask, flash, redirect, render_template, request, session, url_for, abort, g
from werkzeug.security import generate_password_hash, check_password_hash
import os
import sqlite3
import secrets
import string


app.secret_key = os.environ.get("FLASK_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("FLASK_SECRET_KEY is not set")

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

def generate_invite_code(conn, length=10, max_attempts=10):
    """
    Generate a UNIQUE invite code.
    Retries if collision occurs.
    Raises RuntimeError if unable after max_attempts.
    """

    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    cursor = conn.cursor()

    for _ in range(max_attempts):
        code = ''.join(secrets.choice(alphabet) for _ in range(length))

        cursor.execute("SELECT * FROM households WHERE invite_code = ?", (code,))

        if not cursor.fetchone():
            return code

    raise RuntimeError("Unable to generate unique invite code")

def get_available_points(conn, kid_id):
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(points_earned), 0) AS earned
        FROM chore_submissions
        WHERE kid_id = ? AND status = 'approved'
    """, (kid_id,))
    earned = cursor.fetchone()["earned"]

    cursor.execute("""
        SELECT COALESCE(SUM(points_cost), 0) AS spent
        FROM prize_requests
        WHERE kid_id = ? AND status IN ('approved','fulfilled')
    """, (kid_id,))
    spent = cursor.fetchone()["spent"]

    return int(earned) - int(spent)

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

    if user["role"] == "parent" and not user["household_id"]:
        return redirect(url_for("households"))
    
    if user["role"] == "parent" and user["household_id"]:
        return redirect(url_for("parents"))

    return redirect(url_for("kids"))

@app.route("/register", methods=["GET","POST"])
def register():

    if get_current_user():
        return redirect(url_for("index"))

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

        return redirect(url_for("households"))

    else:
        return render_template("register.html")     

@app.route("/households", methods=["GET","POST"])   
def households():

    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))

    if parent["role"] != "parent":
        abort(403)

    if parent["household_id"]:
        return redirect(url_for("parents"))

    if request.method == "POST":

        household = (request.form.get("household") or "").strip()
        invitecode = (request.form.get("invitecode") or "").strip().upper()

        if household and invitecode:
            return render_template("households.html", error="Cannot create a household and join a household")

        elif household:
            with get_db_connection() as conn:
                cursor = conn.cursor()

                # insert household
                cursor.execute("INSERT INTO households (name, invite_code, created_by) VALUES(?, ?, ?)",
                    (household, generate_invite_code(conn), parent["id"]))
                
                new_household_id = cursor.lastrowid

                cursor.execute("UPDATE users SET household_id=? WHERE id=?", (new_household_id, parent["id"]))
        
        elif invitecode:
                with get_db_connection() as conn:
                    cursor = conn.cursor()

                    # check exists
                    cursor.execute("SELECT * FROM households WHERE invite_code = ?", (invitecode,))
                    existing_household = cursor.fetchone()
                    if not existing_household:
                        return render_template("households.html", error="Invite code not found")
                
                    # update parents household
                    cursor.execute("UPDATE users SET household_id = ? WHERE id = ?", (existing_household["id"], parent["id"]))

        else:
            return render_template("households.html", error="Enter a household name or an invite code")
        
        return redirect(url_for("parents"))

    return render_template("households.html")  

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

    if not parent["household_id"]:
        return redirect(url_for("households"))

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
            cursor.execute("INSERT INTO users (username, password_hash, role, household_id) VALUES(?, ?, ?, ?)",
                   (username, generate_password_hash(password), 'kid', parent["household_id"]))

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

    if not kid["household_id"]:
        return redirect(url_for("login"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Points balance (use your helper)
        available_points = get_available_points(conn, kid["id"])

        # Available chores (active)
        cursor.execute("""
            SELECT id, title, points
            FROM chore_templates
            WHERE household_id = ?
              AND active = 'Y'
            ORDER BY title
            LIMIT 6
        """, (kid["household_id"],))
        available_chores = cursor.fetchall()

        # Available prizes (active)
        cursor.execute("""
            SELECT id, title, points_cost
            FROM prize_templates
            WHERE household_id = ?
              AND active = 'Y'
            ORDER BY points_cost, title
            LIMIT 6
        """, (kid["household_id"],))
        available_prizes = cursor.fetchall()

        # Recent activity (two simple lists)
        cursor.execute("""
            SELECT s.id, t.title, s.status, s.points_earned, s.submitted_on
            FROM chore_submissions s
            JOIN chore_templates t ON t.id = s.template_id
            WHERE s.kid_id = ?
            ORDER BY s.submitted_on DESC
            LIMIT 5
        """, (kid["id"],))
        recent_submissions = cursor.fetchall()

        cursor.execute("""
            SELECT r.id, t.title, r.status, r.points_cost, r.requested_on
            FROM prize_requests r
            JOIN prize_templates t ON t.id = r.template_id
            WHERE r.kid_id = ?
            ORDER BY r.requested_on DESC
            LIMIT 5
        """, (kid["id"],))
        recent_requests = cursor.fetchall()

    return render_template(
        "kids.html",
        kid=kid,
        available_points=available_points,
        available_chores=available_chores,
        available_prizes=available_prizes,
        recent_submissions=recent_submissions,
        recent_requests=recent_requests
    )


@app.route("/parents")
def parents():
    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))

    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Kids + computed points (single query; avoids looping get_available_points)
        cursor.execute("""
            SELECT
              u.id AS kid_id,
              u.username AS kid_username,
              (
                COALESCE((
                  SELECT SUM(cs.points_earned)
                  FROM chore_submissions cs
                  WHERE cs.kid_id = u.id AND cs.status = 'approved'
                ), 0)
                -
                COALESCE((
                  SELECT SUM(pr.points_cost)
                  FROM prize_requests pr
                  WHERE pr.kid_id = u.id AND pr.status IN ('approved','fulfilled')
                ), 0)
              ) AS points_balance
            FROM users u
            WHERE u.role = 'kid'
              AND u.household_id = ?
            ORDER BY u.username
        """, (parent["household_id"],))
        kids = cursor.fetchall()

        # Pending chore submissions (household-scoped via chore_templates)
        cursor.execute("""
            SELECT COUNT(*) AS c
            FROM chore_submissions s
            JOIN chore_templates t ON t.id = s.template_id
            WHERE t.household_id = ?
              AND s.status = 'submitted'
        """, (parent["household_id"],))
        pending_submissions = cursor.fetchone()["c"]

        # Pending prize requests (requested only)
        cursor.execute("""
            SELECT COUNT(*) AS c
            FROM prize_requests r
            JOIN prize_templates t ON t.id = r.template_id
            WHERE t.household_id = ?
              AND r.status = 'requested'
        """, (parent["household_id"],))
        pending_requests = cursor.fetchone()["c"]

        cursor.execute("""
            SELECT h.invite_code
            FROM households h
            JOIN users u ON u.household_id = h.id
            WHERE u.id = ?
            AND u.role = 'parent'
        """, (parent["id"],))
        invite = cursor.fetchone()[0]

    return render_template(
        "parents.html",
        parent=parent,
        kids=kids,
        pending_submissions=pending_submissions,
        pending_requests=pending_requests,
        invite=invite
    )

@app.route("/parents/chores", methods=["GET", "POST"])
def parents_chores():

    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))
    
    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # get chore list
        cursor.execute("SELECT id, title, points, active FROM chore_templates WHERE household_id = ? ORDER BY active DESC, title", (parent["household_id"],))
        chores = cursor.fetchall()
    
        if request.method == "POST":

            choretitle = (request.form.get("choretitle") or "").strip()
            chorepoints = request.form.get("chorepoints")

            if not choretitle:
                return render_template("parent-chores.html", chores=chores, error="Missing chore title")
            
            if not chorepoints:
                return render_template("parent-chores.html", chores=chores, error="Missing chore points")
            
            try:
                points_chk = int(chorepoints)
            except (TypeError, ValueError):
                return render_template("parent-chores.html", chores=chores, error="Points must be a positive integer")
            
            if points_chk < 1:
                return render_template("parent-chores.html", chores=chores, error="Points must be a positive integer")

            # check if chore already exists
            cursor.execute("SELECT * FROM chore_templates WHERE household_id = ? AND title = ?", (parent["household_id"], choretitle))
            existing_chore = cursor.fetchone()
            if existing_chore:
                return render_template("parent-chores.html", chores=chores, error="Chore title already exists")
            
            # insert new chore template
            cursor.execute("INSERT INTO chore_templates (household_id, title, points, active, created_by) VALUES (?, ? ,?, ?, ?)",
                (parent["household_id"], choretitle, points_chk, 'Y', parent["id"]))
                
            flash("Chore created", "success")
            return redirect(url_for("parents_chores"))

    return render_template("parent-chores.html", chores=chores)

@app.route("/parents/chores/<int:chore_id>/toggle", methods=["POST"])
def toggle_chore(chore_id):
    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))

    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE chore_templates
            SET active = CASE active WHEN 'Y' THEN 'N' ELSE 'Y' END
            WHERE id = ?
            AND household_id = ?
        """, (chore_id, parent["household_id"]))

        if cursor.rowcount != 1:
            abort(403)

    flash("Chore updated", "success")
    return redirect(url_for("parents_chores"))

@app.route("/kids/chores", methods=["GET"])
def kids_chores():
    kid = get_current_user()

    if not kid:
        return redirect(url_for("login"))

    if kid["role"] != "kid":
        abort(403)

    if not kid["household_id"]:
        return redirect(url_for("login"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Active templates for this household
        cursor.execute("SELECT id, title, points FROM chore_templates WHERE household_id = ? AND active = 'Y' ORDER BY title", (kid["household_id"],))
        templates = cursor.fetchall()

        # Recent submissions for this kid
        cursor.execute("""
            SELECT s.id, t.title, s.status, s.note, s.points_earned, s.submitted_on, s.reviewed_on
            FROM chore_submissions s
            JOIN chore_templates t ON t.id = s.template_id
            WHERE s.kid_id = ?
            ORDER BY s.submitted_on DESC
            LIMIT 25
        """, (kid["id"],))
        submissions = cursor.fetchall()

    return render_template("kids-chores.html", templates=templates, submissions=submissions)


@app.route("/kids/chores/submit", methods=["POST"])
def submit_chore():
    kid = get_current_user()

    if not kid:
        return redirect(url_for("login"))

    if kid["role"] != "kid":
        abort(403)

    if not kid["household_id"]:
        return redirect(url_for("login"))

    template_id = request.form.get("template_id")
    note = (request.form.get("note") or "").strip()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Security check: template must belong to kid household and be active
        cursor.execute("""
            SELECT 1
            FROM chore_templates
            WHERE id = ? AND household_id = ? AND active = 'Y'
        """, (template_id, kid["household_id"]))

        if not cursor.fetchone():
            abort(403)

        cursor.execute("""
            INSERT INTO chore_submissions (template_id, kid_id, status, note, points_earned, submitted_on)
            VALUES (?, ?, 'submitted', ?, NULL, CURRENT_TIMESTAMP)
        """, (template_id, kid["id"], note))

    flash("Chore submitted!", "success")
    return redirect(url_for("kids_chores"))


@app.route("/parents/submissions", methods=["GET"])
def parent_submissions():
    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))
    
    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.id, s.note, s.submitted_on,
                   k.username AS kid_username,
                   t.title AS chore_title,
                   t.points AS template_points
            FROM chore_submissions s
            JOIN chore_templates t ON t.id = s.template_id
            JOIN users k ON k.id = s.kid_id
            WHERE t.household_id = ?
              AND s.status = 'submitted'
            ORDER BY s.submitted_on ASC
        """, (parent["household_id"],))
        pending = cursor.fetchall()

        cursor.execute("""
            SELECT s.id, s.status, s.note, s.points_earned, s.submitted_on, s.reviewed_on,
                   k.username AS kid_username,
                   t.title AS chore_title
            FROM chore_submissions s
            JOIN chore_templates t ON t.id = s.template_id
            JOIN users k ON k.id = s.kid_id
            WHERE t.household_id = ?
              AND s.status IN ('approved','denied')
            ORDER BY s.reviewed_on DESC
            LIMIT 25
        """, (parent["household_id"],))
        reviewed = cursor.fetchall()

    return render_template("parents-submissions.html", pending=pending, reviewed=reviewed)


@app.route("/parents/submissions/<int:submission_id>/review", methods=["POST"])
def review_submission(submission_id):

    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))
    
    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    decision = (request.form.get("decision") or "").strip().lower()
    if decision not in ("approved", "denied"):
        abort(403)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE chore_submissions
            SET status = ?,
                points_earned = CASE
                    WHEN ? = 'approved' THEN (SELECT points FROM chore_templates WHERE id = chore_submissions.template_id)
                    ELSE 0
                END,
                reviewed_by = ?,
                reviewed_on = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = 'submitted'
              AND template_id IN (
                  SELECT id FROM chore_templates WHERE household_id = ?
              )
        """, (decision, decision, parent["id"], submission_id, parent["household_id"]))

        if cursor.rowcount != 1:
            abort(403)

    flash(f"Submission {decision}.", "success")
    return redirect(url_for("parent_submissions"))

@app.route("/parents/prizes", methods=["GET", "POST"])
def parents_prizes():

    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))
    
    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # get prize list
        cursor.execute("SELECT id, title, points_cost, active FROM prize_templates WHERE household_id = ? ORDER BY active DESC, title", (parent["household_id"],))
        prizes = cursor.fetchall()
    
        if request.method == "POST":

            prizetitle = (request.form.get("prizetitle") or "").strip()
            prizepoints = request.form.get("prizepoints")

            if not prizetitle:
                return render_template("parent-prizes.html", prizes=prizes, error="Missing chore title")
            
            if not prizepoints:
                return render_template("parent-prizes.html", prizes=prizes, error="Missing chore points")
            
            try:
                points_chk = int(prizepoints)
            except (TypeError, ValueError):
                return render_template("parent-prizes.html", prizes=prizes, error="Points must be a positive integer")
            
            if points_chk < 1:
                return render_template("parent-prizes.html", prizes=prizes, error="Points must be a positive integer")

            # check if chore already exists
            cursor.execute("SELECT * FROM prize_templates WHERE household_id = ? AND title = ?", (parent["household_id"], prizetitle))
            existing_prize = cursor.fetchone()
            if existing_prize:
                return render_template("parent-prizes.html", prizes=prizes, error="Chore title already exists")
            
            # insert new chore template
            cursor.execute("INSERT INTO prize_templates (household_id, title, points_cost, active, created_by) VALUES (?, ? ,?, ?, ?)",
                (parent["household_id"], prizetitle, points_chk, 'Y', parent["id"]))
                
            flash("Prize created", "success")
            return redirect(url_for("parents_prizes"))

    return render_template("parent-prizes.html", prizes=prizes)

@app.route("/parents/prizes/<int:prize_id>/toggle", methods=["POST"])
def toggle_prize(prize_id):
    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))

    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE prize_templates
            SET active = CASE active WHEN 'Y' THEN 'N' ELSE 'Y' END
            WHERE id = ?
            AND household_id = ?
        """, (prize_id, parent["household_id"]))

        if cursor.rowcount != 1:
            abort(403)

    flash("Prize updated", "success")
    return redirect(url_for("parents_prizes"))

@app.route("/kids/prizes", methods=["GET"])
def kids_prizes():
    kid = get_current_user()

    if not kid:
        return redirect(url_for("login"))

    if kid["role"] != "kid":
        abort(403)

    if not kid["household_id"]:
        return redirect(url_for("login"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Active templates for this household
        cursor.execute("SELECT id, title, points_cost FROM prize_templates WHERE household_id = ? AND active = 'Y' ORDER BY title", (kid["household_id"],))
        templates = cursor.fetchall()

        available = get_available_points(conn, kid["id"])  

        # Recent submissions for this kid
        cursor.execute("""
            SELECT s.id, t.title, s.status, s.note, s.points_cost, s.requested_on, s.reviewed_on, s.fulfilled_on
            FROM prize_requests s
            JOIN prize_templates t ON t.id = s.template_id
            WHERE s.kid_id = ?
            ORDER BY s.requested_on DESC
            LIMIT 25
        """, (kid["id"],))
        submissions = cursor.fetchall()

    return render_template("kids-prizes.html", templates=templates, available=available, submissions=submissions)


@app.route("/kids/prizes/submit", methods=["POST"])
def submit_prize():
    kid = get_current_user()

    if not kid:
        return redirect(url_for("login"))

    if kid["role"] != "kid":
        abort(403)

    if not kid["household_id"]:
        return redirect(url_for("login"))

    template_id = request.form.get("template_id")
    note = (request.form.get("note") or "").strip()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT points_cost FROM prize_templates WHERE id = ? AND household_id = ? AND active = 'Y'", (template_id, kid["household_id"]))
        row = cursor.fetchone()
        if not row:
            abort(403)

        points_cost = row["points_cost"]

        available = get_available_points(conn, kid["id"])
        if available < points_cost:
            flash("Not enough points", "danger")
            return redirect(url_for("kids_prizes"))

        cursor.execute("""
            INSERT INTO prize_requests (template_id, kid_id, status, note, points_cost, requested_on)
            VALUES (?, ?, 'requested', ?, ?, CURRENT_TIMESTAMP)
        """, (template_id, kid["id"], note, points_cost))

    flash("Prize submitted!", "success")
    return redirect(url_for("kids_prizes"))


@app.route("/parents/requests", methods=["GET"])
def parent_requests():
    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))
    
    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    with get_db_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT s.id, s.status, s.note, s.points_cost, s.requested_on, s.reviewed_on, s.fulfilled_on,
                k.username AS kid_username,
                t.title AS prize_title
            FROM prize_requests s
            JOIN prize_templates t ON t.id = s.template_id
            JOIN users k ON k.id = s.kid_id
            WHERE t.household_id = ?
            AND s.status IN ('requested','approved')
            ORDER BY
            CASE s.status WHEN 'requested' THEN 0 ELSE 1 END,
            s.requested_on ASC
        """, (parent["household_id"],))
        pending = cursor.fetchall()

        cursor.execute("""
            SELECT s.id, s.status, s.note, s.points_cost, s.requested_on, s.reviewed_on, s.fulfilled_on,
                k.username AS kid_username,
                t.title AS prize_title
            FROM prize_requests s
            JOIN prize_templates t ON t.id = s.template_id
            JOIN users k ON k.id = s.kid_id
            WHERE t.household_id = ?
            AND s.status IN ('denied','fulfilled')
            ORDER BY
            COALESCE(s.fulfilled_on, s.reviewed_on) DESC
            LIMIT 25
        """, (parent["household_id"],))
        reviewed = cursor.fetchall()

    return render_template("parents-requests.html", pending=pending, reviewed=reviewed)


@app.route("/parents/requests/<int:request_id>/review", methods=["POST"])
def review_requests(request_id):

    parent = get_current_user()

    if not parent:
        return redirect(url_for("login"))
    
    if parent["role"] != "parent":
        abort(403)

    if not parent["household_id"]:
        return redirect(url_for("households"))

    decision = (request.form.get("decision") or "").strip().lower()
    if decision not in ("approved", "denied", "fulfilled"):
        abort(400)

    with get_db_connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        cursor = conn.cursor()

        if decision in ("approved", "denied"):
            # Load the pending request to check points before approval
            cursor.execute("""
                SELECT r.id, r.kid_id, r.points_cost
                FROM prize_requests r
                JOIN prize_templates t ON t.id = r.template_id
                WHERE r.id = ?
                  AND r.status = 'requested'
                  AND t.household_id = ?
            """, (request_id, parent["household_id"]))
            req = cursor.fetchone()
            if not req:
                abort(403)

            if decision == "approved":
                available = get_available_points(conn, req["kid_id"])
                if available < req["points_cost"]:
                    flash("Not enough points to approve this request.", "danger")
                    return redirect(url_for("parent_requests"))

            cursor.execute("""
                UPDATE prize_requests
                SET status = ?,
                    reviewed_by = ?,
                    reviewed_on = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND status = 'requested'
            """, (decision, parent["id"], request_id))

        elif decision == "fulfilled":
            cursor.execute("""
                UPDATE prize_requests
                SET status = 'fulfilled',
                    fulfilled_on = CURRENT_TIMESTAMP
                WHERE id = ?
                  AND status = 'approved'
                  AND template_id IN (
                      SELECT id FROM prize_templates WHERE household_id = ?
                  )
            """, (request_id, parent["household_id"]))

        if cursor.rowcount != 1:
            abort(403)

    flash(f"Request {decision}.", "success")
    return redirect(url_for("parent_requests"))

@app.route("/logout")
def logout():

    session.clear()
    flash("Logged out")
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)