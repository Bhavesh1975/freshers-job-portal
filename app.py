from flask import Flask, render_template, session, request, flash, url_for, redirect, jsonify, make_response
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.message import EmailMessage
from collections import Counter
import random
import math
import datetime
import os
from werkzeug.utils import secure_filename
import pdfplumber
import re
import docx
import requests
from openai import OpenAI
import secrets
import hashlib
import csv
import io


app = Flask(__name__)
app.secret_key = "Shree"

app.jinja_env.globals.update(max=max, min=min)

app.config['UPLOAD_FOLDER'] = os.path.join('static', 'profile_pics')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

app.config['RESUME_FOLDER'] = os.path.join('static','resumes')
os.makedirs(app.config['RESUME_FOLDER'], exist_ok=True)

app.config['CHECKER_FOLDER'] = os.path.join('static','resumes','checker')
os.makedirs(app.config['CHECKER_FOLDER'], exist_ok=True)

client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

# API_KEY = "2b945c2c7emsha9f21d8f257cfabp141d62jsnffe0f473ee24"

ADZUNA_APP_ID  = "eaacffc9"   # from developer.adzuna.com
ADZUNA_APP_KEY = "98ad6f7eaa388958e0bc0351672da129"

def get_connection():
    return mysql.connector.connect(
        host="jobportal-db.cv66ssaw4nnq.eu-north-1.rds.amazonaws.com",
        port="3306",
        user="admin",
        password="freshers2026",
        database="Job_Portal",
        connection_timeout=60
    )

# ── Email helper (reuses same SMTP as OTP) ──────────────────────────────────
SMTP_EMAIL    = "fresherjobportal.noreply@gmail.com"
SMTP_PASSWORD = "uhripksznktbfzth"

def send_email(to_email, subject, body):
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = SMTP_EMAIL
    msg['To']      = to_email
    msg.set_content(body)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send to {to_email}: {e}")


def setup_database():
    connection = get_connection()
    cursor = connection.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS registers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    Full_Name VARCHAR(70),
    mobile VARCHAR(15),
    password VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    profile_image VARCHAR(255) DEFAULT 'default.png',
    bio TEXT,
    linkedin VARCHAR(255),
    github VARCHAR(255)
)
    """)
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS jobs (
    id INT NOT NULL AUTO_INCREMENT,
    job_title VARCHAR(100),
    company VARCHAR(100),
    industry VARCHAR(100),
    city VARCHAR(100),
    experience VARCHAR(50),
    employment VARCHAR(50),
    work_mode VARCHAR(50),
    company_email VARCHAR(150),
    description TEXT,
    posted_date DATE,
    PRIMARY KEY (id)
)""")
    
    cursor.execute("""
                   CREATE TABLE IF NOT EXISTS job_applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    job_id INT,
    name VARCHAR(100),
    email VARCHAR(100),
    phone VARCHAR(20),
    city VARCHAR(100),
    age varchar(10),
    qualification VARCHAR(100),
    experience INT,
    current_company VARCHAR(100),
    expected_salary INT,
    linkedin VARCHAR(255),
    portfolio VARCHAR(255),
    notice_period VARCHAR(50),
    relocate VARCHAR(10),
    resume VARCHAR(255),
    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS remember_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    token_hash VARCHAR(255),
    expires_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)""")
    
    cursor.execute("""
CREATE TABLE IF NOT EXISTS password_resets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255),
    token_hash VARCHAR(255),
    expires_at DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS questions (
    id INT PRIMARY KEY,
    question TEXT,
    topic VARCHAR(100),
    subtopic VARCHAR(100),
    level VARCHAR(20),
    type VARCHAR(20),
    solution LONGTEXT
);""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS options (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT,
    option_text TEXT,
    option_index INT,
    FOREIGN KEY (question_id) REFERENCES questions(id)
)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS answers (
    question_id INT PRIMARY KEY,
    answer_index INT,
    FOREIGN KEY (question_id) REFERENCES questions(id)
)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS subjective_questions (
    question_id INT PRIMARY KEY,
    sample_answer TEXT,
    keywords TEXT,
    model_answer TEXT,
    FOREIGN KEY (question_id) REFERENCES questions(id)
)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS test_schedules (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    job_id      INT NOT NULL,
    duration    INT DEFAULT 30,
    date_1      DATE,
    date_2      DATE,
    slot_1      TIME,
    slot_2      TIME,
    slot_3      TIME,
    status      ENUM('draft','scheduled','live') DEFAULT 'draft',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS test_questions (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    job_id          INT NOT NULL,
    question        TEXT NOT NULL,
    option_1        VARCHAR(500),
    option_2        VARCHAR(500),
    option_3        VARCHAR(500),
    option_4        VARCHAR(500),
    option_5        VARCHAR(500),
    option_6        VARCHAR(500),
    correct_answer  INT NOT NULL,
    solution        TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
)""")
    
    cursor.execute("""CREATE TABLE IF NOT EXISTS test_invites (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    job_id          INT NOT NULL,
    applicant_id    INT NOT NULL,
    slot_date       DATE,
    slot_time       TIME,
    status          ENUM('pending','scheduled','completed','terminated') DEFAULT 'pending',
    score           INT DEFAULT 0,
    invited_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    token           VARCHAR(64) UNIQUE,
    total_questions INT Default NULL,
    completed_at     DATETIME     DEFAULT NULL,
    UNIQUE KEY unique_invite (job_id, applicant_id),
    FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE,
    FOREIGN KEY (applicant_id) REFERENCES job_applications(id) ON DELETE CASCADE
)""")
    
    cursor.execute("SHOW COLUMNS FROM job_applications LIKE 'status'")
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE job_applications ADD COLUMN status VARCHAR(50) DEFAULT 'applied'")

    cursor.execute("SHOW COLUMNS FROM job_applications LIKE 'rejection_reason'")
    if not cursor.fetchone():
            cursor.execute("ALTER TABLE job_applications ADD COLUMN rejection_reason TEXT DEFAULT NULL")

    connection.commit()
    cursor.close()
    connection.close()


setup_database()

@app.before_request
def auto_login():
    if 'user_id' in session:
        return

    token = request.cookies.get("remember_token")
    if not token:
        return

    token_hash = hashlib.sha256(token.encode()).hexdigest()
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT user_id FROM remember_tokens
        WHERE token_hash = %s AND expires_at > NOW()
    """, (token_hash,))
    record = cursor.fetchone()

    if record:
        cursor.execute(
            "SELECT id, Email, role FROM registers WHERE id = %s",
            (record['user_id'],)
        )
        user = cursor.fetchone()
        if user:
            session['user_id']    = user['id']
            session['user_email'] = user['Email']
            session['role']       = user['role']

    cursor.close()
    conn.close()


@app.route('/')
def home():
    if 'user_email' in session:
        return redirect(url_for('main'))

    token = request.cookies.get("remember_token")

    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT user_id FROM remember_tokens
            WHERE token_hash = %s AND expires_at > NOW()
        """, (token_hash,))

        record = cursor.fetchone()

        if record:
            cursor.execute(
                "SELECT id, Email, role FROM registers WHERE id=%s",
                (record['user_id'],)
            )
            user = cursor.fetchone()
            if user:
                session['user_id']    = user['id']
                session['user_email'] = user['Email']
                session['role']       = user['role']

                cursor.close()
                conn.close()
                return redirect(url_for('main'))

        cursor.close()
        conn.close()

    return render_template("index.html", show_form="login")


@app.route('/register', methods=['POST'])
def register():
    full_name        = request.form.get('name')
    mobile           = request.form.get('mobile')
    email            = request.form.get('email')
    password         = request.form.get('password')
    confirm_password = request.form.get('confirm_password')
    role             = request.form.get('role', 'user')

    if password != confirm_password:
        flash("Passwords do not match!")
        return render_template("index.html", show_form="register")

    session['pending_user'] = {
        "full_name": full_name,
        "mobile":    mobile,
        "email":     email,
        "password":  password,
        "role":      role
    }

    otp = "".join(str(random.randint(0, 9)) for _ in range(4))
    session["otp"] = otp

    msg = EmailMessage()
    msg.set_content(f"Your OTP is: {otp}")
    msg["Subject"] = "OTP Verification"
    msg["From"]    = SMTP_EMAIL
    msg["To"]      = email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
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
    user_otp     = request.form.get("otp")
    saved_otp    = session.get("otp")
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
            "INSERT INTO registers (Full_Name, mobile, Email, password, role) VALUES (%s, %s, %s, %s, %s)",
            (
                pending_user["full_name"],
                pending_user["mobile"],
                pending_user["email"],
                hashed_password,
                pending_user["role"]
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


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form.get('email')
        password = request.form.get('password')

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT id, Email, password, role FROM registers WHERE Email = %s",
            (email,)
        )

        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and check_password_hash(user['password'], password):
            session['user_id']    = user['id']
            session['user_email'] = user['Email']
            session['role']       = user['role']

            remember = request.form.get("remember")
            response = make_response(redirect(url_for('main')))

            if remember:
                token      = secrets.token_hex(32)
                token_hash = hashlib.sha256(token.encode()).hexdigest()
                expiry     = datetime.datetime.now() + datetime.timedelta(days=30)

                conn   = get_connection()
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO remember_tokens (user_id, token_hash, expires_at)
                    VALUES (%s, %s, %s)
                """, (user['id'], token_hash, expiry))

                conn.commit()
                cursor.close()
                conn.close()

                response.set_cookie(
                    "remember_token",
                    token,
                    expires=expiry,
                    httponly=True,
                    secure=False
                )

            return response

        else:
            flash("Invalid Email or Password")
            return render_template("index.html", show_form="login")

    return render_template("index.html", show_form="login")


@app.context_processor
def inject_user():
    if 'user_email' in session:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT Full_Name, Email, profile_image FROM registers WHERE Email = %s",
            (session['user_email'],)
        )

        user = cursor.fetchone()
        cursor.close()
        connection.close()

        return dict(current_user=user)

    return dict(current_user=None)


@app.route('/main')
def main():
    if 'user_email' not in session:
        token = request.cookies.get("remember_token")

        if token:
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            conn   = get_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
            SELECT user_id FROM remember_tokens
            WHERE token_hash = %s AND expires_at > NOW()
            """, (token_hash,))

            record = cursor.fetchone()

            if record:
                cursor.execute(
                    "SELECT id, Email, role FROM registers WHERE id=%s",
                    (record['user_id'],)
                )
                user = cursor.fetchone()
                if user:
                    session['user_id']    = user['id']
                    session['user_email'] = user['Email']
                    session['role']       = user['role']

            cursor.close()
            conn.close()

    if 'user_email' not in session:
        return redirect(url_for('home'))

    page     = request.args.get('page', 1, type=int)
    per_page = 16

    job  = request.args.get('job', '')
    city = request.args.get('city', '')
    mode = request.args.get('mode', '')

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT DISTINCT job_title FROM jobs")
    job_titles = cursor.fetchall()

    cursor.execute("SELECT DISTINCT city FROM jobs")
    cities = cursor.fetchall()

    query  = "FROM jobs WHERE 1=1"
    params = []

    if job:
        query += " AND job_title LIKE %s"
        params.append(f"%{job}%")

    if city:
        query += " AND city LIKE %s"
        params.append(f"%{city}%")

    if mode:
        query += " AND work_mode LIKE %s"
        params.append(f"%{mode}%")

    cursor.execute("SELECT COUNT(*) as total " + query, params)
    total_jobs  = cursor.fetchone()['total']
    total_pages = math.ceil(total_jobs / per_page)

    offset = (page - 1) * per_page

    cursor.execute(
        "SELECT * " + query + " ORDER BY posted_date DESC LIMIT %s OFFSET %s",
        params + [per_page, offset]
    )

    jobs = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template(
        "main.html",
        jobs=jobs,
        page=page,
        total_pages=total_pages,
        job_titles=job_titles,
        cities=cities,
        job=job,
        city=city,
        mode=mode
    )


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/post', methods=['GET', 'POST'])
def post():
    if session.get('role') != 'recruiter':
        return "Access Denied"

    if request.method == 'POST':

        job_title    = request.form.get("job_title")
        company      = request.form.get("company")
        industry     = request.form.get("industry")
        city         = request.form.get("city")
        experience   = request.form.get("experience")
        employment   = request.form.get("employment")
        work_mode    = request.form.get("work_mode")
        company_email = request.form.get("email")
        description  = request.form.get("description")
        posted_date  = datetime.datetime.now()

        if not job_title:
            flash("Invalid submission")
            return redirect(url_for('post'))

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO jobs
            (job_title, company, industry, city, experience, employment, work_mode, company_email, description, posted_date)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            job_title, company, industry, city,
            experience, employment, work_mode,
            company_email, description, posted_date
        ))

        connection.commit()
        cursor.close()
        connection.close()

        return redirect(url_for('main'))

    return render_template('post.html')


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    if 'profile_image' not in request.files:
        flash("No file selected")
        return redirect(url_for('profile'))

    file = request.files['profile_image']

    if file.filename == '':
        flash("No file selected")
        return redirect(url_for('profile'))

    if file and allowed_file(file.filename):
        filename  = secure_filename(file.filename)
        extension = filename.rsplit('.', 1)[1].lower()
        filename  = f"{session['user_id']}.{extension}"

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        conn   = get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE registers SET profile_image=%s WHERE id=%s",
                       (filename, session['user_id']))
        conn.commit()

        flash("Profile image updated!")
    else:
        flash("Invalid file type!")

    return redirect(url_for('profile'))


@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect(url_for('home'))

    mobile   = request.form.get('mobile')
    bio      = request.form.get('bio')
    linkedin = request.form.get('linkedin')
    github   = request.form.get('github')

    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE registers
        SET mobile=%s, bio=%s, linkedin=%s, github=%s
        WHERE id=%s
    """, (mobile, bio, linkedin, github, session['user_id']))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('profile'))


@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect(url_for('login'))

    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM registers WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('profile.html', user=user)


ALLOWED_RESUME = {'pdf', 'doc', 'docx'}

def allowed_resume(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_RESUME


@app.route("/apply/<int:id>", methods=['GET', 'POST'])
def apply_job(id):
    if 'user_id' not in session:
        flash("Please login first")
        return redirect(url_for('login'))

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT Full_Name, mobile, email, linkedin FROM registers WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()

    if request.method == 'POST':

        name  = user['Full_Name']
        email = user['email']
        phone = user['mobile']

        city             = request.form['city']
        age              = request.form['age']
        qualification    = request.form['qualification']
        experience       = request.form['experience']
        current_company  = request.form['current_company']
        expected_salary  = request.form['expected_salary']
        notice_period    = request.form['notice_period']
        linkedin         = user['linkedin'] if user['linkedin'] else request.form['linkedin']
        portfolio        = request.form.get('portfolio', None)
        relocate         = request.form['relocate']

        resume_file = request.files.get('resume')
        filename    = None

        if resume_file and resume_file.filename != "":
            if not allowed_resume(resume_file.filename):
                flash("Only PDF, DOC, DOCX files allowed")
                return redirect(request.url)

            filename    = f"{session['user_id']}_{secure_filename(resume_file.filename)}"
            resume_path = os.path.join(app.config['RESUME_FOLDER'], filename)
            resume_file.save(resume_path)

        query = """
        INSERT INTO job_applications
        (job_id,name,email,phone,city,age,qualification,experience,current_company,
        expected_salary,linkedin,portfolio,notice_period,relocate,resume)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """

        values = (
            id, name, email, phone, city, age, qualification, experience, current_company,
            expected_salary, linkedin, portfolio, notice_period, relocate, filename
        )

        cursor.execute(query, values)
        connection.commit()

        flash("Application submitted successfully!")
        return redirect(url_for('main'))

    cursor.execute("SELECT * FROM jobs WHERE id=%s", (id,))
    job = cursor.fetchone()

    cursor.close()
    connection.close()

    if not job:
        return "Job not found", 404

    return render_template("apply_job.html", job=job, user=user)


@app.route('/resume_checker', methods=["GET", "POST"])
def resume_checker():
    if session.get('role') != 'user':
        return "Access Denied"

    score = None

    if request.method == "POST":

        job_description = request.form['job_description'].lower()
        file = request.files["resume"]

        if file.filename == "":
            flash("Please upload a resume")
            return redirect(request.url)

        filepath = os.path.join(app.config["CHECKER_FOLDER"], file.filename)
        file.save(filepath)

        text     = ""
        filename = file.filename.lower()

        if filename.endswith(".pdf"):
            with pdfplumber.open(filepath) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text

        elif filename.endswith(".docx"):
            doc = docx.Document(filepath)
            for para in doc.paragraphs:
                text += para.text

        text = text.lower()

        parts = re.split(r',|\band\b|\n', job_description)

        stopwords = [
            "i","want","skills","like","required","looking","for",
            "candidate","experience","years","year","with",
            "the","and","role","job","work","team","will","have"
        ]

        job_skills = []

        for phrase in parts:
            words = phrase.strip().split()
            for word in words:
                if word not in stopwords and len(word) > 2:
                    job_skills.append(word)

        job_skills = list(set(job_skills))

        matched = []
        for skill in job_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text):
                matched.append(skill)

        missing = [skill for skill in job_skills if skill not in matched]

        total = len(job_skills)
        score = 0 if total == 0 else int((len(matched) / total) * 100)

        suggestions = []
        if missing:
            suggestions.append("Add missing skills: " + ", ".join(missing[:5]))
        if "project" not in text:
            suggestions.append("Add project section")
        if "experience" not in text:
            suggestions.append("Include experience section")
        if "education" not in text:
            suggestions.append("Add education details")
        if "certification" not in text:
            suggestions.append("Add certifications")
        if score > 80:
            suggestions.append("Great resume! Minor improvements needed.")

        keywords_count = len(set(text.split()))

        exp_match = re.search(r'(\d+(\.\d+)?)\+?\s*(years|year|yrs)', text)
        if exp_match:
            experience = exp_match.group(0)
        elif "fresher" in text:
            experience = "Fresher"
        else:
            experience = "Not Mentioned"

        education        = "Not Found"
        degree_patterns  = {
            r'\bbca\b|bachelor of computer applications': "BCA",
            r'\bmca\b|master of computer applications':  "MCA",
            r'\bb\.?tech\b|bachelor of technology':      "B.Tech",
            r'\bm\.?tech\b|master of technology':        "M.Tech",
            r'\bbachelor\b':                              "Bachelor's Degree",
            r'\bmaster\b':                                "Master's Degree"
        }

        for pattern, value in degree_patterns.items():
            if re.search(pattern, text):
                education = value
                break

        return render_template(
            "resume_checker.html",
            score=score,
            matched=matched,
            missing=missing,
            total=total,
            suggestions=suggestions,
            keywords_count=keywords_count,
            experience=experience,
            education=education
        )

    return render_template("resume_checker.html", score=None)


cache = {}


def fetch_jobs(job_title):
    url = "https://api.adzuna.com/v1/api/jobs/in/search/1"
    params = {
        "app_id":           ADZUNA_APP_ID,
        "app_key":          ADZUNA_APP_KEY,
        "what":             job_title,
        "content-type":     "application/json",
        "results_per_page": 50,
    }
    try:
        response = requests.get(url, params=params)
        data = response.json()
        return data.get("results", [])   # ← "results" not "data"
    except Exception as e:
        print("Adzuna Error:", e)
        return []


def analyze_data(jobs):
    skills = [
        # ── IT & Software ──────────────────────────
        "python", "java", "javascript", "c++", "c#", "php", "ruby", "swift",
        "react", "angular", "node", "django", "flask", "spring",
        "sql", "mysql", "mongodb", "postgresql",
        "aws", "azure", "docker", "kubernetes", "git",
        "machine learning", "deep learning", "ai", "data science",
        "html", "css", "typescript", "rest api",

        # ── Data & Analytics ───────────────────────
        "power bi", "tableau", "excel", "data analysis",
        "pandas", "numpy", "r programming", "spark", "hadoop",

        # ── Finance & Accounting ───────────────────
        "tally", "gst", "accounting", "auditing", "taxation",
        "financial analysis", "ms excel", "sap", "balance sheet",
        "bookkeeping", "payroll", "tds", "ifrs",

        # ── Marketing & Sales ──────────────────────
        "digital marketing", "seo", "social media", "content writing",
        "google ads", "email marketing", "lead generation",
        "sales", "crm", "market research", "brand management",
        "copywriting", "ppc", "affiliate marketing",

        # ── HR & Management ────────────────────────
        "recruitment", "hr", "performance management",
        "training", "employee engagement", "talent acquisition",
        "ms office", "communication", "leadership",

        # ── Engineering (Non-IT) ───────────────────
        "autocad", "solidworks", "catia", "ansys",
        "mechanical design", "civil engineering", "structural analysis",
        "electrical", "plc", "scada", "embedded systems",
        "quality control", "six sigma", "lean manufacturing",
        "project management", "primavera",

        # ── Healthcare & Pharma ────────────────────
        "clinical research", "pharmacovigilance", "medical coding",
        "nursing", "patient care", "laboratory", "radiology",
        "drug regulatory", "gmp", "pharmacology",

        # ── Logistics & Operations ─────────────────
        "supply chain", "inventory management", "warehouse",
        "procurement", "logistics", "erp",

        # ── Design & Media ─────────────────────────
        "photoshop", "illustrator", "figma", "canva",
        "video editing", "after effects", "ui/ux", "graphic design",

        # ── Education & Soft Skills ────────────────
        "teaching", "curriculum", "e-learning",
        "presentation", "teamwork", "problem solving",
    ]

    skill_list = []
    city_list  = []

    for job in jobs:
        if not isinstance(job, dict):
            continue

        # ← Adzuna uses "description" not "job_description"
        desc = (job.get("description") or "").lower()

        if len(desc) < 50:
            continue

        for skill in skills:
            pattern = r'\b' + re.escape(skill) + r'\b'
            if re.search(pattern, desc):
                skill_list.append(skill)

        # ← Adzuna uses nested location object not "job_city"
        location = job.get("location", {})
        city = location.get("display_name") or "Unknown"
        city_list.append(city)

    return dict(Counter(skill_list)), dict(Counter(city_list))


@app.route('/analytics')
def analytics():
    connection = get_connection()
    cursor     = connection.cursor()

    cursor.execute("SELECT DISTINCT job_title FROM jobs")
    job_titles = [row[0] for row in cursor.fetchall()]

    return render_template("analytics.html", job_titles=job_titles)


@app.route('/api/analytics')
def api_analytics():
    job_title = request.args.get('job')

    if job_title in cache:
        return jsonify(cache[job_title])

    jobs                  = fetch_jobs(job_title)
    skill_data, city_data = analyze_data(jobs)

    cleaned_cities = {}
    for city, count in city_data.items():
        if city and city.strip().lower() not in ["", "unknown", "none", "null"]:
            cleaned_cities[city] = count
        else:
            cleaned_cities["Other"] = cleaned_cities.get("Other", 0) + count

    city_data = cleaned_cities

    if not skill_data:
        skill_data = {"No Data": 1}
    if not city_data:
        city_data = {"No Data": 1}

    top_skill = max(skill_data, key=skill_data.get)

    result = {
        "skills":    skill_data,
        "cities":    city_data,
        "top_skill": top_skill
    }

    cache[job_title] = result
    return jsonify(result)


@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message")

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a helpful job assistant."},
                {"role": "user",   "content": user_msg}
            ]
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"reply": "⚠️ Error connecting to AI"})


def send_reset_email(to_email, reset_link):
    msg = EmailMessage()
    msg['Subject'] = "Password Reset Request"
    msg['From']    = SMTP_EMAIL
    msg['To']      = to_email

    msg.set_content(f"""
Hello,

Click the link below to reset your password: 
{reset_link}

This link will expire in 15 minutes.
""")

    with smtplib.SMTP('smtp.gmail.com', 587) as smtp:
        smtp.starttls()
        smtp.login(SMTP_EMAIL, SMTP_PASSWORD)
        smtp.send_message(msg)


@app.route('/forget', methods=['POST'])
def forget_password():
    email = request.form.get('email')

    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM registers WHERE email=%s", (email,))
    user = cursor.fetchone()

    if not user:
        flash("Email not found", "danger")
        return redirect(url_for('login'))

    cursor.execute("DELETE FROM password_resets WHERE email=%s", (email,))

    token      = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    expires_at = datetime.datetime.utcnow() + datetime.timedelta(minutes=15)

    cursor.execute("""
        INSERT INTO password_resets (email, token_hash, expires_at)
        VALUES (%s, %s, %s)
    """, (email, token_hash, expires_at))

    conn.commit()

    reset_link = url_for('reset_password_page', token=token, _external=True)
    send_reset_email(email, reset_link)

    cursor.close()
    conn.close()

    flash("Reset link sent to your email", "success")
    return redirect(url_for('login'))


@app.route('/reset-password/<token>', methods=['GET'])
def reset_password_page(token):
    return render_template('reset-password.html', token=token)


@app.route('/reset-password', methods=['GET'])
def reset_password_invalid():
    flash("Invalid or expired access", "danger")
    return redirect(url_for('login'))


@app.route('/reset-password', methods=['POST'])
def reset_password():
    token            = request.form.get('token')
    new_password     = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if not token:
        flash("Invalid request", "danger")
        return redirect(url_for('login'))

    if new_password != confirm_password:
        flash("Passwords do not match", "danger")
        return redirect(request.referrer)

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email FROM password_resets
        WHERE token_hash=%s AND expires_at > NOW()
    """, (token_hash,))

    result = cursor.fetchone()

    if not result:
        flash("Invalid or expired link", "danger")
        return redirect(url_for('login'))

    email           = result[0]
    hashed_password = generate_password_hash(new_password)

    cursor.execute("UPDATE registers SET password=%s WHERE email=%s", (hashed_password, email))
    cursor.execute("DELETE FROM password_resets WHERE email=%s", (email,))
    conn.commit()

    cursor.close()
    conn.close()

    flash("Password updated successfully", "success")
    return redirect(url_for('login'))


@app.route('/learning')
def learning():
    return render_template('learning.html')


@app.route('/get_topics')
def get_topics():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("SELECT topic, subtopic, level FROM questions")
    rows = cursor.fetchall()

    topics_dict = {}

    for row in rows:
        topic = row['topic']
        sub   = row['subtopic']
        level = row['level']

        if topic not in topics_dict:
            topics_dict[topic] = {}
        if sub not in topics_dict[topic]:
            topics_dict[topic][sub] = set()

        topics_dict[topic][sub].add(level)

    data = []
    for topic, subs in topics_dict.items():
        subtopics_list = []
        for sub, levels in subs.items():
            subtopics_list.append({
                "name":       sub,
                "difficulty": list(levels)
            })
        data.append({"topic": topic, "subtopics": subtopics_list})

    cursor.close()
    connection.close()

    return jsonify(data)


@app.route('/practice/<topic>/<subtopic>/<difficulty>')
def practice(topic, subtopic, difficulty):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM questions
        WHERE topic=%s AND subtopic=%s AND level=%s
        ORDER BY RAND()
        LIMIT 15
    """, (topic, subtopic, difficulty))

    questions = cursor.fetchall()

    for q in questions:
        q['type'] = q['type'].lower().strip()

        if q['type'] == 'mcq':
            cursor.execute("""
                SELECT option_text, option_index
                FROM options
                WHERE question_id=%s
                ORDER BY option_index
            """, (q['id'],))
            q['options'] = cursor.fetchall()

            cursor.execute("SELECT answer_index FROM answers WHERE question_id=%s", (q['id'],))
            ans = cursor.fetchone()
            q['answer_index'] = ans['answer_index'] if ans else None
            q['sample_answer'] = ""
            q['keywords']      = ""
            q['model_answer']  = ""

        elif q['type'] in ('subjective', 'interview', 'open_ended'):
            q['type'] = 'subjective'

            cursor.execute("""
                SELECT sample_answer, keywords, model_answer
                FROM subjective_questions
                WHERE question_id=%s
            """, (q['id'],))
            sub = cursor.fetchone()
            if sub:
                q['sample_answer'] = sub['sample_answer'] or ""
                q['keywords']      = sub['keywords']      or ""
                q['model_answer']  = sub['model_answer']  or ""
            else:
                q['sample_answer'] = ""
                q['keywords']      = ""
                q['model_answer']  = ""
            q['answer_index'] = None
            q['options']      = []
            q['solution']     = ""

    cursor.close()
    connection.close()

    return render_template("practice.html", questions=questions)


@app.route('/test/start')
def test_start():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    questions  = []
    categories = ['Aptitude', 'Reasoning', 'Verbal']

    for category in categories:
        cursor.execute("""
            SELECT * FROM questions
            WHERE topic = %s AND type = 'mcq'
            ORDER BY RAND()
            LIMIT 10
        """, (category,))
        questions += cursor.fetchall()

    random.shuffle(questions)

    for q in questions:
        q['type'] = q['type'].lower().strip()

        cursor.execute("""
            SELECT option_text, option_index
            FROM options
            WHERE question_id = %s
            ORDER BY option_index
        """, (q['id'],))
        q['options'] = cursor.fetchall()

        cursor.execute("SELECT answer_index FROM answers WHERE question_id = %s", (q['id'],))
        ans = cursor.fetchone()
        q['answer_index'] = ans['answer_index'] if ans else None
        q['solution']      = q.get('solution') or ''
        q['sample_answer'] = ''
        q['keywords']      = ''
        q['model_answer']  = ''

    cursor.close()
    connection.close()

    return render_template("test.html", questions=questions, duration=30)


# ════════════════════════════════════════════════════════
#  HIRING HUB
# ════════════════════════════════════════════════════════

@app.route('/hiring_hub')
def hiring_hub():
    if not session.get('user_email') or session.get('role') != 'recruiter':
        return redirect(url_for('login'))

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    recruiter_email = session.get('user_email')

    cursor.execute("""
        SELECT * FROM jobs
        WHERE company_email = %s
        ORDER BY posted_date DESC
    """, (recruiter_email,))
    jobs = cursor.fetchall()

    total_applicants = 0
    tests_scheduled  = 0
    tests_completed  = 0

    for job in jobs:
        # ── Applicants ──────────────────────────────────
        cursor.execute("""
    SELECT ja.id, ja.name, ja.email, ja.city, ja.experience, ja.qualification, ja.resume,
           COALESCE(ti.status, 'pending')     AS slot_status,
           COALESCE(ja.status, 'applied')     AS app_status,
           ja.rejection_reason,
           ti.slot_date, ti.slot_time, ti.score
    FROM job_applications ja
    LEFT JOIN test_invites ti
        ON ti.applicant_id = ja.id AND ti.job_id = ja.job_id
    WHERE ja.job_id = %s
""", (job['id'],))
        applicants = cursor.fetchall()

        for app in applicants:
            app['slot_time']        = str(app['slot_time']) if app['slot_time'] else ''
            app['score']            = app['score'] or 0
            app['resume']           = '/static/resumes/' + app['resume'] if app.get('resume') else '#'
            app['app_status']       = app.get('app_status') or 'applied'
            app['rejection_reason'] = app.get('rejection_reason') or ''

        job['applicants']     = applicants
        job['applicant_count'] = len(applicants)

        # ── Test schedule ────────────────────────────────
        cursor.execute("SELECT * FROM test_schedules WHERE job_id = %s", (job['id'],))
        schedule = cursor.fetchone()

        if schedule:
            job['test_status']   = schedule['status']
            job['test_duration'] = schedule['duration']
            job['date_1']        = str(schedule['date_1']) if schedule['date_1'] else ''
            job['date_2']        = str(schedule['date_2']) if schedule['date_2'] else ''
            job['slot_1']        = str(schedule['slot_1']) if schedule['slot_1'] else ''
            job['slot_2']        = str(schedule['slot_2']) if schedule['slot_2'] else ''
            job['slot_3']        = str(schedule['slot_3']) if schedule['slot_3'] else ''
        else:
            job['test_status']   = 'none'
            job['test_duration'] = 30
            job['date_1'] = job['date_2'] = ''
            job['slot_1'] = job['slot_2'] = job['slot_3'] = ''

        # ── Question count ───────────────────────────────
        cursor.execute("SELECT COUNT(*) as cnt FROM test_questions WHERE job_id = %s", (job['id'],))
        job['total_questions'] = cursor.fetchone()['cnt']

        # ── Stats counters ───────────────────────────────
        total_applicants += len(applicants)
        if job['test_status'] in ('scheduled', 'live'):
            tests_scheduled += 1
        completed_count = sum(1 for a in applicants if a['slot_status'] == 'completed')
        tests_completed += completed_count

    cursor.close()
    connection.close()

    return render_template("hiring_hub.html",
        jobs=jobs,
        total_applicants=total_applicants,
        tests_scheduled=tests_scheduled,
        tests_completed=tests_completed
    )


# ── Replace your send_email function with this HTML version ──────────────────

def send_email(to_email, subject, body_text, body_html=None):
    """Send plain text or HTML email via SMTP."""
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From']    = SMTP_EMAIL
    msg['To']      = to_email

    # Plain text fallback
    msg.set_content(body_text)

    # HTML version (shown if email client supports it)
    if body_html:
        msg.add_alternative(body_html, subtype='html')

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"[EMAIL ERROR] Could not send to {to_email}: {e}")


# ─────────────────────────────────────────────────────────────────────────────


@app.route('/hiring-hub/schedule', methods=['POST'])
def hiring_hub_schedule():
    if not session.get('user_email') or session.get('role') != 'recruiter':
        return redirect(url_for('login'))

    job_id   = request.form.get('job_id')
    action   = request.form.get('action')
    duration = request.form.get('duration', 30)
    date_1   = request.form.get('date_1') or None
    date_2   = request.form.get('date_2') or None
    slot_1   = request.form.get('slot_1') or None
    slot_2   = request.form.get('slot_2') or None
    slot_3   = request.form.get('slot_3') or None

    status = 'scheduled' if action == 'save' else 'draft'

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # ── Save / update schedule ───────────────────────────
    cursor.execute("SELECT id FROM test_schedules WHERE job_id = %s", (job_id,))
    existing = cursor.fetchone()

    if existing:
        cursor.execute("""
            UPDATE test_schedules
            SET duration=%s, date_1=%s, date_2=%s,
                slot_1=%s, slot_2=%s, slot_3=%s, status=%s
            WHERE job_id=%s
        """, (duration, date_1, date_2, slot_1, slot_2, slot_3, status, job_id))
    else:
        cursor.execute("""
            INSERT INTO test_schedules
                (job_id, duration, date_1, date_2, slot_1, slot_2, slot_3, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (job_id, duration, date_1, date_2, slot_1, slot_2, slot_3, status))

    # ── Save questions ───────────────────────────────────
    cursor.execute("DELETE FROM test_questions WHERE job_id = %s", (job_id,))
    questions_saved = 0

    csv_file = request.files.get('csv_file')
    if csv_file and csv_file.filename.endswith('.csv'):
        stream = io.StringIO(csv_file.stream.read().decode('utf-8'))
        reader = csv.DictReader(stream)
        for row in reader:
            cursor.execute("""
                INSERT INTO test_questions
                    (job_id, question, option_1, option_2, option_3,
                     option_4, option_5, option_6, correct_answer, solution)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                job_id,
                row.get('question', ''),
                row.get('option_1', ''), row.get('option_2', ''),
                row.get('option_3', ''), row.get('option_4', ''),
                row.get('option_5', ''), row.get('option_6', ''),
                row.get('correct_answer', 1),
                row.get('solution', '')
            ))
            questions_saved += 1

    manual_texts = request.form.getlist(f'mq_text_{job_id}[]')
    manual_ans   = request.form.getlist(f'mq_ans_{job_id}[]')
    manual_sols  = request.form.getlist(f'mq_sol_{job_id}[]')
    manual_opts  = request.form.getlist(f'mq_opt_{job_id}[]')

    if manual_texts and any(t.strip() for t in manual_texts):
        opts_per_q = len(manual_opts) // len(manual_texts) if manual_texts else 4
        for i, qtext in enumerate(manual_texts):
            if not qtext.strip():
                continue
            start = i * opts_per_q
            opts  = manual_opts[start:start + opts_per_q]
            opts += [''] * (6 - len(opts))
            cursor.execute("""
                INSERT INTO test_questions
                    (job_id, question, option_1, option_2, option_3,
                     option_4, option_5, option_6, correct_answer, solution)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                job_id, qtext,
                opts[0], opts[1], opts[2], opts[3], opts[4], opts[5],
                manual_ans[i] if i < len(manual_ans) else 1,
                manual_sols[i] if i < len(manual_sols) else ''
            ))
            questions_saved += 1

    bank_topic = request.form.get('bank_topic')
    bank_level = request.form.get('bank_level')
    bank_count = request.form.get('bank_count')

    if bank_count and int(bank_count) > 0:
        q_query = """
            SELECT q.id, q.question, q.solution,
                   a.answer_index AS correct_answer
            FROM questions q
            JOIN answers a ON a.question_id = q.id
            WHERE q.type = 'mcq'
        """
        q_params = []
        if bank_topic:
            q_query += " AND q.topic = %s"
            q_params.append(bank_topic)
        if bank_level:
            q_query += " AND q.level = %s"
            q_params.append(bank_level)
        q_query += " ORDER BY RAND()"
        cursor.execute(q_query, q_params)
        bank_qs  = cursor.fetchall()
        selected = random.sample(bank_qs, min(int(bank_count), len(bank_qs)))

        for q in selected:
            # Fetch options from the options table
            cursor.execute("""
                SELECT option_text FROM options
                WHERE question_id = %s
                ORDER BY option_index
                LIMIT 6
            """, (q['id'],))
            opts = [row['option_text'] for row in cursor.fetchall()]
            opts += [''] * (6 - len(opts))  # pad to 6 slots

            cursor.execute("""
                INSERT INTO test_questions
                    (job_id, question, option_1, option_2, option_3,
                     option_4, option_5, option_6, correct_answer, solution)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                job_id, q['question'],
                opts[0], opts[1], opts[2], opts[3], opts[4], opts[5],
                q['correct_answer'], q.get('solution', '')
            ))
            questions_saved += 1

    # ── Send invites if action == 'save' ─────────────────
    if action == 'save' and (date_1 or date_2) and slot_1:

        cursor.execute("""
            SELECT ja.id, ja.name, ja.email
            FROM job_applications ja
            WHERE ja.job_id = %s
        """, (job_id,))
        applicants = cursor.fetchall()

        cursor.execute("SELECT job_title, company FROM jobs WHERE id = %s", (job_id,))
        job_info = cursor.fetchone()

        # Build all available slots
        slots_available = []
        for d in [date_1, date_2]:
            if d:
                for s in [slot_1, slot_2, slot_3]:
                    if s:
                        slots_available.append((str(d), str(s)[:5]))

        for app in applicants:
            token = secrets.token_urlsafe(32)

            cursor.execute("""
                INSERT INTO test_invites (job_id, applicant_id, status, token)
                VALUES (%s, %s, 'pending', %s)
                ON DUPLICATE KEY UPDATE status='pending', token=%s
            """, (job_id, app['id'], token, token))

            # ── Build HTML buttons for each slot ─────────
            buttons_html = ""
            plain_links  = ""
            for (d, s) in slots_available:
                link = url_for('confirm_slot', token=token, date=d, time=s, _external=True)
                buttons_html += f"""
                <a href="{link}" style="
                    display: block;
                    margin: 10px 0;
                    padding: 14px 20px;
                    background: linear-gradient(135deg, #4f46e5, #7c3aed);
                    color: #ffffff !important;
                    text-decoration: none;
                    border-radius: 10px;
                    font-size: 15px;
                    font-weight: 600;
                    text-align: center;
                    font-family: Arial, sans-serif;
                ">
                    📅 {d} &nbsp;&nbsp; 🕐 {s}
                </a>"""
                plain_links += f"\n  {d} at {s}: {link}\n"

            # ── Plain text version ────────────────────────
            body_text = f"""Hi {app['name']},

Congratulations! You have been shortlisted for an online assessment.

  Company  : {job_info['company']}
  Role     : {job_info['job_title']}
  Duration : {duration} minutes

Please select your preferred slot by visiting one of the links below:
{plain_links}

Each link can only be used once. Once you click, your slot is locked in.

Best of luck!
Team {job_info['company']}
"""

            # ── HTML version with buttons ─────────────────
            body_html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:520px;margin:40px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.1);">

    <!-- Header -->
    <div style="background:linear-gradient(135deg,#4f46e5,#7c3aed);padding:32px 40px;text-align:center;">
      <h1 style="color:#ffffff;margin:0;font-size:22px;">🎯 Test Invitation</h1>
      <p style="color:#c7d2fe;margin:8px 0 0;font-size:14px;">{job_info['company']}</p>
    </div>

    <!-- Body -->
    <div style="padding:32px 40px;">
      <p style="font-size:15px;color:#374151;margin:0 0 8px;">Hi <strong>{app['name']}</strong>,</p>
      <p style="font-size:14px;color:#6b7280;margin:0 0 24px;">
        Congratulations! You have been shortlisted for an online assessment for the role of
        <strong style="color:#4f46e5;">{job_info['job_title']}</strong>.
      </p>

      <!-- Info box -->
      <div style="background:#f0f4ff;border-left:4px solid #4f46e5;border-radius:8px;padding:16px 20px;margin-bottom:28px;">
        <p style="margin:0 0 8px;font-size:13px;color:#374151;">🏢 <strong>Company:</strong> {job_info['company']}</p>
        <p style="margin:0 0 8px;font-size:13px;color:#374151;">💼 <strong>Role:</strong> {job_info['job_title']}</p>
        <p style="margin:0;font-size:13px;color:#374151;">⏱ <strong>Duration:</strong> {duration} minutes</p>
      </div>

      <!-- Slot selection -->
      <p style="font-size:14px;font-weight:700;color:#111827;margin:0 0 12px;text-transform:uppercase;letter-spacing:0.5px;">
        Select Your Preferred Slot
      </p>
      <p style="font-size:13px;color:#6b7280;margin:0 0 16px;">
        Click on a slot button below to confirm your test date and time:
      </p>

      {buttons_html}

      <p style="font-size:12px;color:#9ca3af;margin:20px 0 0;padding-top:16px;border-top:1px solid #f1f5f9;">
        ⚠️ Each button can only be used once. Once you click, your slot is locked in.
      </p>
    </div>

    <!-- Footer -->
    <div style="background:#f9fafb;padding:20px 40px;text-align:center;border-top:1px solid #f1f5f9;">
      <p style="font-size:12px;color:#9ca3af;margin:0;">Best of luck! — Team {job_info['company']}</p>
    </div>

  </div>
</body>
</html>
"""
            send_email(app['email'],
                       f"Test Invitation – {job_info['job_title']} at {job_info['company']}",
                       body_text,
                       body_html)

    connection.commit()
    cursor.close()
    connection.close()

    if action == 'save':
        flash('Test scheduled and invites sent successfully!', 'success')
    else:
        flash('Draft saved successfully!', 'info')

    return redirect(url_for('hiring_hub'))


# ── Applicant clicks slot button from email ──────────────────────────────────
@app.route('/confirm-slot')
def confirm_slot():
    token = request.args.get('token')
    date  = request.args.get('date')
    time  = request.args.get('time')

    if not token or not date or not time:
        return "Invalid link.", 400

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute("""
        SELECT ti.*, ja.name, ja.email, j.job_title, j.company, ts.duration
        FROM test_invites ti
        JOIN job_applications ja ON ja.id = ti.applicant_id
        JOIN jobs j              ON j.id  = ti.job_id
        JOIN test_schedules ts   ON ts.job_id = ti.job_id
        WHERE ti.token = %s
    """, (token,))
    invite = cursor.fetchone()

    if not invite:
        cursor.close()
        connection.close()
        return "This link is invalid or has already been used.", 404

    if invite['status'] == 'scheduled' and invite['slot_date']:
        cursor.close()
        connection.close()
        return "You have already confirmed your slot. Please check your email.", 200

    # Save selected slot and clear token
    cursor.execute("""
        UPDATE test_invites
        SET slot_date=%s, slot_time=%s, status='scheduled', token=NULL
        WHERE token=%s
    """, (date, time, token))

    connection.commit()

    # ── Send confirmation email ───────────────────────────
    body_text = f"""Hi {invite['name']},

Your test slot has been confirmed!

  Company  : {invite['company']}
  Role     : {invite['job_title']}
  Date     : {date}
  Time     : {time}
  Duration : {invite['duration']} minutes

Please be ready 5 minutes before your slot.

Best of luck!
Team {invite['company']}
"""

    body_html = f"""
<!DOCTYPE html>
<html>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,sans-serif;">
  <div style="max-width:480px;margin:40px auto;background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.1);">

    <div style="background:linear-gradient(135deg,#22c55e,#16a34a);padding:32px 40px;text-align:center;">
      <div style="font-size:48px;margin-bottom:8px;">✅</div>
      <h1 style="color:#ffffff;margin:0;font-size:22px;">Slot Confirmed!</h1>
    </div>

    <div style="padding:32px 40px;">
      <p style="font-size:15px;color:#374151;margin:0 0 20px;">
        Hi <strong>{invite['name']}</strong>, your test slot has been booked successfully!
      </p>

      <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:12px;padding:20px 24px;">
        <p style="margin:0 0 10px;font-size:14px;color:#374151;">🏢 <strong>Company:</strong> {invite['company']}</p>
        <p style="margin:0 0 10px;font-size:14px;color:#374151;">💼 <strong>Role:</strong> {invite['job_title']}</p>
        <p style="margin:0 0 10px;font-size:14px;color:#374151;">📅 <strong>Date:</strong> {date}</p>
        <p style="margin:0 0 10px;font-size:14px;color:#374151;">🕐 <strong>Time:</strong> {time}</p>
        <p style="margin:0;font-size:14px;color:#374151;">⏱ <strong>Duration:</strong> {invite['duration']} minutes</p>
      </div>

      <p style="font-size:13px;color:#6b7280;margin:20px 0 0;">
        Please be ready 5 minutes before your slot. Keep this email for your reference.
      </p>
    </div>

    <div style="background:#f9fafb;padding:20px 40px;text-align:center;border-top:1px solid #f1f5f9;">
      <p style="font-size:12px;color:#9ca3af;margin:0;">Best of luck! — Team {invite['company']}</p>
    </div>

  </div>
</body>
</html>
"""

    send_email(invite['email'],
               f"✅ Slot Confirmed – {invite['job_title']} at {invite['company']}",
               body_text,
               body_html)

    cursor.close()
    connection.close()

    return "Your slot has been confirmed! A confirmation email has been sent to your inbox.", 200

# ════════════════════════════════════════════════════════

# ── Add these routes to your app.py ─────────────────────────────────────────
# Place them near your existing /my_applications route


@app.route('/my_applications')
def my_applications():
    if not session.get('user_email'):
        return redirect(url_for('login'))
    return render_template("my_applications.html")


@app.route('/api/my_applications_data')
def my_applications_data():
    if not session.get('user_email'):
        return {'error': 'Unauthorized'}, 401
 
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
 
    cursor.execute("""
        SELECT id, name FROM job_applications
        WHERE email = %s
        ORDER BY id DESC
    """, (session['user_email'],))
    applicants = cursor.fetchall()
 
    if not applicants:
        cursor.close()
        connection.close()
        return {'tests': [], 'jobs': [], 'name': 'there'}
 
    applicant_ids  = [a['id'] for a in applicants]
    applicant_name = applicants[0]['name']
    fmt = ','.join(['%s'] * len(applicant_ids))
 
    # Tests
    cursor.execute(f"""
        SELECT
            ti.id            AS invite_id,
            ti.slot_date,
            ti.slot_time,
            ti.status        AS invite_status,
            COALESCE(ts.duration, 30) AS duration,
            j.id             AS job_id,
            j.job_title,
            j.company,
            j.city           AS location,
            (SELECT COUNT(*) FROM test_questions tq WHERE tq.job_id = j.id) AS question_count
        FROM test_invites ti
        JOIN jobs j              ON j.id  = ti.job_id
        LEFT JOIN test_schedules ts ON ts.job_id = ti.job_id
        WHERE ti.applicant_id IN ({fmt})
        ORDER BY ti.slot_date ASC, ti.slot_time ASC
    """, applicant_ids)
    tests = cursor.fetchall()
 
    for t in tests:
        t['slot_date'] = str(t['slot_date']) if t['slot_date'] else None
        t['slot_time'] = str(t['slot_time']) if t['slot_time'] else None
 
    # Applied jobs — now includes status + rejection_reason
    cursor.execute(f"""
        SELECT
            ja.id               AS application_id,
            ja.job_id,
            COALESCE(ja.status, 'applied') AS application_status,
            ja.rejection_reason,
            ja.applied_date     AS created_at,
            j.job_title,
            j.company,
            j.city              AS location,
            j.employment        AS job_type,
            j.experience
        FROM job_applications ja
        JOIN jobs j ON j.id = ja.job_id
        WHERE ja.id IN ({fmt})
        ORDER BY ja.applied_date DESC
    """, applicant_ids)
    jobs = cursor.fetchall()
 
    for j in jobs:
        j['created_at'] = str(j['created_at']) if j['created_at'] else None
 
    cursor.close()
    connection.close()
 
    return {'tests': tests, 'jobs': jobs, 'name': applicant_name}


@app.route('/api/exam_questions/<int:job_id>')
def exam_questions(job_id):
    """Returns shuffled questions for the exam. Only accessible if invite is valid."""
    if not session.get('user_email'):
        return {'error': 'Unauthorized'}, 401

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # Verify the user has a scheduled invite for this job
    cursor.execute("""
        SELECT ti.id, ti.slot_date, ti.slot_time, ts.duration
        FROM test_invites ti
        JOIN job_applications ja ON ja.id = ti.applicant_id
        JOIN test_schedules ts   ON ts.job_id = ti.job_id
        WHERE ja.email = %s AND ti.job_id = %s AND ti.status = 'scheduled'
        LIMIT 1
    """, (session['user_email'], job_id))
    invite = cursor.fetchone()

    if not invite:
        cursor.close()
        connection.close()
        return {'error': 'No valid invite found'}, 403

    cursor.execute("""
        SELECT id, question, option_1, option_2, option_3,
               option_4, option_5, option_6, correct_answer
        FROM test_questions
        WHERE job_id = %s
        ORDER BY RAND()
    """, (job_id,))
    questions = cursor.fetchall()

    # Strip correct_answer from response (anti-cheat)
    clean = []
    for q in questions:
        opts = [q[f'option_{i}'] for i in range(1, 7) if q.get(f'option_{i}', '').strip()]
        clean.append({
            'id': q['id'],
            'question': q['question'],
            'options': opts
        })

    cursor.close()
    connection.close()

    return {
        'questions': clean,
        'duration': invite['duration'],
        'slot_date': str(invite['slot_date']),
        'slot_time': str(invite['slot_time'])
    }


@app.route('/api/submit_exam', methods=['POST'])
def submit_exam():
    """Receives answers, scores them, saves result."""
    if not session.get('user_email'):
        return {'error': 'Unauthorized'}, 401

    data    = request.get_json()
    job_id  = data.get('job_id')
    answers = data.get('answers', {})  # {question_id: selected_option_index (1-based)}

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    # Verify invite
    cursor.execute("""
        SELECT ti.id, ti.applicant_id
        FROM test_invites ti
        JOIN job_applications ja ON ja.id = ti.applicant_id
        WHERE ja.email = %s AND ti.job_id = %s AND ti.status = 'scheduled'
        LIMIT 1
    """, (session['user_email'], job_id))
    invite = cursor.fetchone()

    if not invite:
        cursor.close()
        connection.close()
        return {'error': 'Invalid invite'}, 403

    # Fetch correct answers
    q_ids = list(answers.keys())
    if not q_ids:
        return {'score': 0, 'total': 0}

    fmt = ','.join(['%s'] * len(q_ids))
    cursor.execute(f"""
        SELECT id, correct_answer, solution
        FROM test_questions
        WHERE id IN ({fmt}) AND job_id = %s
    """, (*q_ids, job_id))
    db_questions = cursor.fetchall()

    score = 0
    total = len(db_questions)
    result_details = []

    for q in db_questions:
        user_ans  = int(answers.get(str(q['id']), 0))
        correct   = int(q['correct_answer'])
        is_correct = (user_ans == correct)
        if is_correct:
            score += 1
        result_details.append({
            'question_id': q['id'],
            'user_answer':  user_ans,
            'correct':      correct,
            'is_correct':   is_correct,
            'solution':     q.get('solution', '')
        })

    # Save result + mark invite as completed
    cursor.execute("""
        UPDATE test_invites
        SET status = 'completed', score = %s, total_questions = %s, completed_at = NOW()
        WHERE id = %s
    """, (score, total, invite['id']))

    # Also update job_application status
    cursor.execute("""
        UPDATE job_applications
        SET status = 'test_completed'
        WHERE id = %s
    """, (invite['applicant_id'],))

    connection.commit()
    cursor.close()
    connection.close()

    percentage = round((score / total) * 100) if total > 0 else 0
    return {
        'score':      score,
        'total':      total,
        'percentage': percentage,
        'details':    result_details
    }
    

@app.route('/api/update_applicant_status', methods=['POST'])
def update_applicant_status():
    """Recruiter sets status: shortlisted / in_review / rejected (+ reason)"""
    if not session.get('user_email') or session.get('role') != 'recruiter':
        return {'error': 'Unauthorized'}, 401
 
    data             = request.get_json()
    applicant_id     = data.get('applicant_id')
    new_status       = data.get('status')       # shortlisted / in_review / rejected
    rejection_reason = data.get('reason', '')
 
    allowed = ['shortlisted', 'in_review', 'rejected']
    if new_status not in allowed:
        return {'error': 'Invalid status'}, 400
 
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
 
    # Make sure this applicant belongs to one of this recruiter's jobs
    cursor.execute("""
        SELECT ja.id, ja.name, ja.email, j.job_title, j.company
        FROM job_applications ja
        JOIN jobs j ON j.id = ja.job_id
        WHERE ja.id = %s AND j.company_email = %s
    """, (applicant_id, session['user_email']))
    applicant = cursor.fetchone()
 
    if not applicant:
        cursor.close()
        connection.close()
        return {'error': 'Not found'}, 404
 
    cursor.execute("""
        UPDATE job_applications
        SET status = %s, rejection_reason = %s
        WHERE id = %s
    """, (new_status, rejection_reason if new_status == 'rejected' else None, applicant_id))
 
    connection.commit()
 
    # Send notification email to applicant
    if new_status == 'shortlisted':
        subject   = f"🎉 Shortlisted – {applicant['job_title']} at {applicant['company']}"
        body_text = f"""Hi {applicant['name']},
 
Great news! You have been shortlisted for the role of {applicant['job_title']} at {applicant['company']}.
 
The recruiter will be in touch shortly with next steps.
 
Best of luck!
Team {applicant['company']}"""
        body_html = f"""
<div style="font-family:Arial,sans-serif;max-width:480px;margin:40px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.1);">
  <div style="background:linear-gradient(135deg,#22c55e,#16a34a);padding:32px 40px;text-align:center;">
    <div style="font-size:48px;">🎉</div>
    <h1 style="color:#fff;margin:8px 0 0;font-size:22px;">You're Shortlisted!</h1>
  </div>
  <div style="padding:32px 40px;">
    <p style="font-size:15px;color:#374151;">Hi <strong>{applicant['name']}</strong>,</p>
    <p style="font-size:14px;color:#6b7280;">You have been shortlisted for <strong style="color:#4f46e5;">{applicant['job_title']}</strong> at <strong>{applicant['company']}</strong>.</p>
    <p style="font-size:14px;color:#6b7280;">The recruiter will contact you shortly with further details.</p>
  </div>
  <div style="background:#f9fafb;padding:20px 40px;text-align:center;border-top:1px solid #f1f5f9;">
    <p style="font-size:12px;color:#9ca3af;margin:0;">Best of luck! — Team {applicant['company']}</p>
  </div>
</div>"""
 
    elif new_status == 'rejected':
        subject   = f"Application Update – {applicant['job_title']} at {applicant['company']}"
        reason_line = f"\n\nReason: {rejection_reason}" if rejection_reason else ""
        body_text = f"""Hi {applicant['name']},
 
Thank you for applying for {applicant['job_title']} at {applicant['company']}.
 
After careful consideration, we regret to inform you that your application has not been selected at this time.{reason_line}
 
We encourage you to apply for future openings. Best of luck!
 
Team {applicant['company']}"""
        reason_html = f'<div style="background:#fff5f5;border-left:4px solid #ef4444;border-radius:8px;padding:14px 18px;margin-top:16px;"><p style="font-size:13px;color:#991b1b;margin:0;"><strong>Reason:</strong> {rejection_reason}</p></div>' if rejection_reason else ''
        body_html = f"""
<div style="font-family:Arial,sans-serif;max-width:480px;margin:40px auto;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.1);">
  <div style="background:linear-gradient(135deg,#6b7280,#374151);padding:32px 40px;text-align:center;">
    <h1 style="color:#fff;margin:0;font-size:20px;">Application Update</h1>
    <p style="color:#d1d5db;margin:8px 0 0;font-size:14px;">{applicant['company']}</p>
  </div>
  <div style="padding:32px 40px;">
    <p style="font-size:15px;color:#374151;">Hi <strong>{applicant['name']}</strong>,</p>
    <p style="font-size:14px;color:#6b7280;">Thank you for your interest in <strong>{applicant['job_title']}</strong>. After careful review, we regret that your application was not selected at this time.</p>
    {reason_html}
    <p style="font-size:13px;color:#9ca3af;margin-top:16px;">We encourage you to apply for future openings.</p>
  </div>
  <div style="background:#f9fafb;padding:20px 40px;text-align:center;border-top:1px solid #f1f5f9;">
    <p style="font-size:12px;color:#9ca3af;margin:0;">— Team {applicant['company']}</p>
  </div>
</div>"""
    else:
        # in_review — no email needed
        cursor.close()
        connection.close()
        return {'success': True}
 
    send_email(applicant['email'], subject, body_text, body_html)
    cursor.close()
    connection.close()
    return {'success': True}

# ── LOGOUT ──────────────────────────────────────────────
@app.route('/logout')
def logout():
    token = request.cookies.get("remember_token")

    if token:
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        conn   = get_connection()
        cursor = conn.cursor()

        cursor.execute("DELETE FROM remember_tokens WHERE token_hash=%s", (token_hash,))
        conn.commit()

        cursor.close()
        conn.close()

    session.clear()

    response = make_response(redirect(url_for('home')))
    response.delete_cookie("remember_token")

    flash("Logged out successfully")
    return response


# ── RUN ─────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)