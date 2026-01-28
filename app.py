from flask import Flask, render_template, request, redirect, session
import mysql.connector, os

app = Flask(__name__)
app.secret_key = "student_portal_key"

UPLOAD_PHOTO = "static/uploads/profile_photos"
UPLOAD_NOTES = "static/uploads/notes"
UPLOAD_SECRET = "static/uploads/secret_docs"
UPLOAD_LINK_IMG = "static/uploads/link_images"
UPLOAD_SKILLS = "static/uploads/skills_materials"

for p in [UPLOAD_PHOTO, UPLOAD_NOTES, UPLOAD_SECRET, UPLOAD_LINK_IMG, UPLOAD_SKILLS]:
    os.makedirs(p, exist_ok=True)

import os

def get_db():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASS"),
        database=os.getenv("DB_NAME"),
        port=int(os.getenv("DB_PORT", "3306"))
    )


@app.route("/", methods=["GET","POST"])
def login():
    session.clear()   # IMPORTANT: clear old user + vault session

    if request.method == "POST":
        r = request.form["rollno"]
        p = request.form["password"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT rollno,is_admin FROM users WHERE rollno=%s AND password=%s",(r,p))
        u = cur.fetchone()
        if u:
            session["rollno"] = u[0]
            session["is_admin"] = u[1]
            return redirect("/dashboard")
        return "Invalid Login"

    return render_template("login.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        d = request.form
        photo = request.files["photo"]
        name = d["rollno"] + "_" + photo.filename
        photo.save(os.path.join(UPLOAD_PHOTO, name))

        db = get_db()
        cur = db.cursor()
        cur.execute("""INSERT INTO users 
        (rollno, name, qualification, year, branch, semester, college, email, photo, password, is_admin, vault_password)
        VALUES (%s,%s,'B.Tech',%s,%s,%s,%s,%s,%s,%s,0,%s)""",
        (d["rollno"], d["name"], d["year"], d["branch"],
        d["semester"], d["college"], d["email"], name, d["password"], d["vault_password"]))
        db.commit()
        return redirect("/")

    return render_template("register.html")

@app.route("/forgot", methods=["GET","POST"])
def forgot():
    if request.method == "POST":
        r = request.form["rollno"]
        e = request.form["email"]
        np = request.form["newpass"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE rollno=%s AND email=%s",(r,e))
        if cur.fetchone():
            cur.execute("UPDATE users SET password=%s WHERE rollno=%s",(np,r))
            db.commit()
            return redirect("/")
        return "Details not match"

    return render_template("forgot_password.html")
@app.route("/profile")
def profile():
    if "rollno" not in session:
        return redirect("/")

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM users WHERE rollno=%s", (session["rollno"],))
    user = cur.fetchone()

    return render_template("profile.html", user=user)
UPLOAD_NOTES = "static/uploads/notes"
os.makedirs(UPLOAD_NOTES, exist_ok=True)

@app.route("/notes", methods=["GET", "POST"])
def notes():
    if "rollno" not in session:
        return redirect("/")

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        title = request.form["title"]
        category = request.form["category"]
        file = request.files["file"]

        if file.filename != "":
            fname = session["rollno"] + "_" + file.filename
            path = os.path.join(UPLOAD_NOTES, fname)
            file.save(path)

            cur.execute(
                "INSERT INTO notes (rollno, title, category, filename) VALUES (%s,%s,%s,%s)",
                (session["rollno"], title, category, fname)
            )
            db.commit()

    cur.execute("""
        SELECT notes.id, notes.rollno, notes.title, notes.category, notes.filename, users.name
        FROM notes
        JOIN users ON notes.rollno = users.rollno
        ORDER BY notes.id DESC
    """)
    data = cur.fetchall()

    return render_template("notes.html", data=data)

@app.route("/delete_note/<int:id>")
def delete_note(id):
    if "rollno" not in session or session.get("is_admin") != 1:
        return redirect("/notes")

    db = get_db()
    cur = db.cursor()

    # Get filename
    cur.execute("SELECT filename FROM notes WHERE id=%s", (id,))
    row = cur.fetchone()

    if row:
        file_path = os.path.join(UPLOAD_NOTES, row[0])
        if os.path.exists(file_path):
            os.remove(file_path)

        cur.execute("DELETE FROM notes WHERE id=%s", (id,))
        db.commit()

    return redirect("/notes")
@app.route("/vault", methods=["GET", "POST"])
def vault():
    if "rollno" not in session:
        return redirect("/")

    # Check if secret password already in session
    if "vault_auth" not in session:
        return redirect("/vault_login")

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        title = request.form["title"]
        file = request.files["file"]

        if file.filename != "":
            fname = session["rollno"] + "_" + file.filename
            path = os.path.join(UPLOAD_SECRET, fname)
            file.save(path)

            cur.execute(
                "INSERT INTO secret_docs (rollno, title, filename) VALUES (%s,%s,%s)",
                (session["rollno"], title, fname)
            )
            db.commit()

    cur.execute("SELECT * FROM secret_docs WHERE rollno=%s ORDER BY id DESC", (session["rollno"],))
    data = cur.fetchall()

    return render_template("vault.html", data=data)


@app.route("/vault_login", methods=["GET", "POST"])
def vault_login():
    if "rollno" not in session:
        return redirect("/")

    if request.method == "POST":
        secret = request.form["secret"]

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT vault_password FROM users WHERE rollno=%s", (session["rollno"],))
        row = cur.fetchone()

        if row and secret == row[0]:
            session["vault_auth"] = True
            return redirect("/vault")
        else:
            return "Wrong Secret Password"

    return render_template("vault_login.html")



@app.route("/vault_logout")
def vault_logout():
    session.pop("vault_auth", None)
    return redirect("/dashboard")
@app.route("/manage_users")
def manage_users():
    if "rollno" not in session or session.get("is_admin") != 1:
        return redirect("/dashboard")

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT rollno, name, email FROM users WHERE is_admin=0")
    users = cur.fetchall()

    return render_template("manage_users.html", users=users)


@app.route("/delete_user/<rollno>")
def delete_user(rollno):
    if "rollno" not in session or session.get("is_admin") != 1:
        return redirect("/dashboard")

    db = get_db()
    cur = db.cursor()

    # Delete user's notes files
    cur.execute("SELECT filename FROM notes WHERE rollno=%s", (rollno,))
    for (fname,) in cur.fetchall():
        path = os.path.join(UPLOAD_NOTES, fname)
        if os.path.exists(path):
            os.remove(path)
    cur.execute("DELETE FROM notes WHERE rollno=%s", (rollno,))

    # Delete secret docs files
    cur.execute("SELECT filename FROM secret_docs WHERE rollno=%s", (rollno,))
    for (fname,) in cur.fetchall():
        path = os.path.join(UPLOAD_SECRET, fname)
        if os.path.exists(path):
            os.remove(path)
    cur.execute("DELETE FROM secret_docs WHERE rollno=%s", (rollno,))

    # Delete profile photo
    cur.execute("SELECT photo FROM users WHERE rollno=%s", (rollno,))
    row = cur.fetchone()
    if row and row[0]:
        p = os.path.join(UPLOAD_PHOTO, row[0])
        if os.path.exists(p):
            os.remove(p)

    # Delete user
    cur.execute("DELETE FROM users WHERE rollno=%s", (rollno,))
    db.commit()

    return redirect("/manage_users")
@app.route("/dashboard")
def dashboard():
    if "rollno" not in session:
        return redirect("/")

    if session["is_admin"] == 1:
        return render_template("admin_dashboard.html")
    return render_template("dashboard.html")
@app.route("/timetable", methods=["GET", "POST"])
def timetable():
    if "rollno" not in session:
        return redirect("/")

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        day = request.form["day"]
        subject = request.form["subject"]
        time_from = request.form["time_from"]
        time_to = request.form["time_to"]

        cur.execute(
            "INSERT INTO timetable (rollno, day, subject, time_from, time_to) VALUES (%s,%s,%s,%s,%s)",
            (session["rollno"], day, subject, time_from, time_to)
        )
        db.commit()

    cur.execute(
        "SELECT * FROM timetable WHERE rollno=%s ORDER BY FIELD(day,'Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'), time_from",
        (session["rollno"],)
    )
    data = cur.fetchall()

    return render_template("timetable.html", data=data)


@app.route("/delete_timetable/<int:id>")
def delete_timetable(id):
    if "rollno" not in session:
        return redirect("/")

    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM timetable WHERE id=%s AND rollno=%s", (id, session["rollno"]))
    db.commit()
    return redirect("/timetable")
# ---------- Apps / Govt Schemes / Skill Links ----------
@app.route("/links/<cat>", methods=["GET", "POST"])
def links(cat):
    if "rollno" not in session:
        return redirect("/")

    db = get_db()
    cur = db.cursor()

    # Admin can add
    if request.method == "POST" and session.get("is_admin") == 1:
        title = request.form["title"]
        url = request.form["url"]
        img = request.files["image"]

        if img.filename != "":
            fname = "link_" + img.filename
            path = os.path.join(UPLOAD_LINK_IMG, fname)
            img.save(path)

            cur.execute(
                "INSERT INTO links (title, url, image, category) VALUES (%s,%s,%s,%s)",
                (title, url, fname, cat)
            )
            db.commit()

        return redirect(f"/links/{cat}")

    # Show only selected category
    cur.execute("SELECT * FROM links WHERE category=%s ORDER BY id DESC", (cat,))
    data = cur.fetchall()

    return render_template("links.html", data=data, cat=cat)



@app.route("/delete_link/<int:id>/<cat>")
def delete_link(id, cat):
    if "rollno" not in session or session.get("is_admin") != 1:
        return redirect(f"/links/{cat}")

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT image FROM links WHERE id=%s", (id,))
    row = cur.fetchone()
    if row:
        img_path = os.path.join(UPLOAD_LINK_IMG, row[0])
        if os.path.exists(img_path):
            os.remove(img_path)

    cur.execute("DELETE FROM links WHERE id=%s", (id,))
    db.commit()

    # go back to same category page
    return redirect(f"/links/{cat}")
# ---------- Skill Videos & Links (Admin only) ----------
@app.route("/skills/videos", methods=["GET", "POST"])
def skill_videos():
    if "rollno" not in session:
        return redirect("/")

    db = get_db()
    cur = db.cursor()

    if request.method == "POST" and session.get("is_admin") == 1:
        title = request.form["title"]
        url = request.form["url"]

        cur.execute(
            "INSERT INTO skills_content (type, title, url, uploaded_by) VALUES ('video', %s, %s, %s)",
            (title, url, session["rollno"])
        )
        db.commit()
        return redirect("/skills/videos")

    cur.execute("SELECT * FROM skills_content WHERE type='video' ORDER BY id DESC")
    data = cur.fetchall()
    return render_template("skills_videos.html", data=data)


@app.route("/delete_skill/<int:id>/video")
def delete_skill_video(id):
    if "rollno" not in session or session.get("is_admin") != 1:
        return redirect("/skills/videos")

    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM skills_content WHERE id=%s AND type='video'", (id,))
    db.commit()
    return redirect("/skills/videos")


# ---------- Skill Notes & Books (Admin + Students upload) ----------
@app.route("/skills/materials", methods=["GET", "POST"])
def skill_materials():
    if "rollno" not in session:
        return redirect("/")

    db = get_db()
    cur = db.cursor()

    if request.method == "POST":
        title = request.form["title"]
        file = request.files["file"]

        if file.filename != "":
            fname = session["rollno"] + "_" + file.filename
            path = os.path.join(UPLOAD_SKILLS, fname)
            file.save(path)

            cur.execute(
                "INSERT INTO skills_content (type, title, filename, uploaded_by) VALUES ('material', %s, %s, %s)",
                (title, fname, session["rollno"])
            )
            db.commit()
        return redirect("/skills/materials")

    cur.execute("SELECT * FROM skills_content WHERE type='material' ORDER BY id DESC")
    data = cur.fetchall()
    return render_template("skills_materials.html", data=data)


@app.route("/delete_skill/<int:id>/material")
def delete_skill_material(id):
    if "rollno" not in session or session.get("is_admin") != 1:
        return redirect("/skills/materials")

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT filename FROM skills_content WHERE id=%s AND type='material'", (id,))
    row = cur.fetchone()
    if row and row[0]:
        p = os.path.join(UPLOAD_SKILLS, row[0])
        if os.path.exists(p):
            os.remove(p)

    cur.execute("DELETE FROM skills_content WHERE id=%s AND type='material'", (id,))
    db.commit()
    return redirect("/skills/materials")
@app.route("/delete_vault/<int:id>")
def delete_vault(id):
    if "rollno" not in session or "vault_auth" not in session:
        return redirect("/vault_login")

    db = get_db()
    cur = db.cursor()

    cur.execute(
        "SELECT filename FROM secret_docs WHERE id=%s AND rollno=%s",
        (id, session["rollno"])
    )
    row = cur.fetchone()

    if row:
        path = os.path.join(UPLOAD_SECRET, row[0])
        if os.path.exists(path):
            os.remove(path)

        cur.execute(
            "DELETE FROM secret_docs WHERE id=%s AND rollno=%s",
            (id, session["rollno"])
        )
        db.commit()

    return redirect("/vault")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# Railway / Gunicorn entry point
application = app



