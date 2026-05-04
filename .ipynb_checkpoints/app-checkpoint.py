from flask import Flask, render_template, session, request, flash, url_for, redirect
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.message import EmailMessage
import random

app = Flask(__name__)
app.secret_key = "Shree"


def get_connection():
    return mysql.connector.connect(
        host="34.44.22.73",
        port="3306",
        user="root",
        password="@Fresherjob2026",
        database="fresher_portal",
        connection_timeout=60
    )


def setup_database():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registers (
            Email VARCHAR(70) PRIMARY KEY,
            Full_Name VARCHAR(70),
            mobile VARCHAR(15),
            password VARCHAR(255)
        )
    """)
    connection.commit()
    cursor.close()
    connection.close()


setup_database()



@app.route('/')
def home():
    return render_template("index.html", show_form="login")



@app.route('/register', methods=['POST'])
def register():
    full_name = request.form.get('name')
    mobile = request.form.get('mobile')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password != confirm_password:
        flash("Passwords do not match!")
        return render_template("index.html", show_form="register")

    # Store temporary user
    session['pending_user'] = {
        "full_name": full_name,
        "mobile": mobile,
        "email": email,
        "password": password
    }

    # Generate OTP
    otp = "".join(str(random.randint(0, 9)) for _ in range(4))
    session["otp"] = otp

    # Send OTP Email
    msg = EmailMessage()
    msg.set_content(f"Your OTP is: {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"] = "bsbhavesh1975@gmail.com"
    msg["To"] = email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login("bsbhavesh1975@gmail.com", "sfruzogwpiyrjcjh")
        server.send_message(msg)
        server.quit()
        flash("OTP sent to your email!")
    except Exception as e:
        print("Email Error:", e)
        flash("Failed to send OTP")
        return render_template("index.html", show_form="register")

    return render_template("index.html", show_form="verify")



@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    user_otp = request.form.get("otp")
    saved_otp = session.get("otp")
    pending_user = session.get("pending_user")

    if not pending_user or not saved_otp:
        flash("Session expired. Register again.")
        return render_template("index.html", show_form="register")

    if user_otp == saved_otp:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT Email FROM registers WHERE Email = %s",
            (pending_user["email"],)
        )

        if cursor.fetchone():
            flash("Email already registered")
            cursor.close()
            connection.close()
            session.clear()
            return render_template("index.html", show_form="register")

        hashed_password = generate_password_hash(pending_user["password"])

        cursor.execute(
            "INSERT INTO registers (Full_Name, mobile, Email, password) VALUES (%s, %s, %s, %s)",
            (
                pending_user["full_name"],
                pending_user["mobile"],
                pending_user["email"],
                hashed_password
            )
        )

        connection.commit()
        cursor.close()
        connection.close()

        session.clear()
        flash("Registration successful! Please login.")
        return render_template("index.html", show_form="login")

    else:
        flash("Invalid OTP")
        return render_template("index.html", show_form="verify")



@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute(
        "SELECT Email, password FROM registers WHERE Email = %s",
        (email,)
    )

    user = cursor.fetchone()
    cursor.close()
    connection.close()

    if user and check_password_hash(user['password'], password):
        session['user_email'] = user['Email']
        return redirect(url_for('main'))
    else:
        flash("Invalid Email or Password")
        return render_template("index.html", show_form="login")


@app.route('/main')
def main():
    if 'user_email' not in session:
        return redirect(url_for('home'))
    return render_template("main.html")


# ---------------- LOGOUT ----------------
# @app.route('/logout')
# def logout():
#     session.clear()
#     flash("Logged out successfully")
#     return redirect(url_for('home'))


# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)

@app.route('/ping')
def ping():
    return "PING OK FROM APP.PY"