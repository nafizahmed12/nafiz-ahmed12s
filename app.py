from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Render Environment Variables থেকে Secret Key নেবে
app.secret_key = os.getenv("SECRET_KEY")


# =========================
# DATABASE
# =========================

def create_database():
    connection = sqlite3.connect("messages.db")
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            message TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()


# Server চালু হওয়ার সময় database/table তৈরি করবে
create_database()


# =========================
# HOME
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# CONTACT
# =========================

@app.route("/contact", methods=["POST"])
def contact():

    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    message = request.form.get("message", "").strip()

    if not name or not email or not message:
        return "All fields are required.", 400

    connection = sqlite3.connect("messages.db")
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT INTO messages (name, email, message)
        VALUES (?, ?, ?)
        """,
        (name, email, message)
    )

    connection.commit()
    connection.close()

    print("Message saved successfully!")

    return "Message saved successfully!"


# =========================
# LOGIN
# =========================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username", "")
        password = request.form.get("password", "")

        # Render Environment Variables
        admin_username = os.getenv("ADMIN_USERNAME")
        admin_password = os.getenv("ADMIN_PASSWORD")

        if username == admin_username and password == admin_password:

            session["admin_logged_in"] = True

            return redirect("/admin")

        return "Invalid username or password.", 401

    return render_template("login.html")


# =========================
# ADMIN
# =========================

@app.route("/admin")
def admin():

    if not session.get("admin_logged_in"):
        return redirect("/login")

    connection = sqlite3.connect("messages.db")
    connection.row_factory = sqlite3.Row

    cursor = connection.cursor()

    cursor.execute(
        "SELECT * FROM messages ORDER BY id DESC"
    )

    messages = cursor.fetchall()

    connection.close()

    return render_template(
        "admin.html",
        messages=messages
    )


# =========================
# LOGOUT
# =========================

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")


# =========================
# LOCAL DEVELOPMENT
# =========================

if __name__ == "__main__":
    app.run()