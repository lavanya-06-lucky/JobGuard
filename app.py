from flask import Flask, render_template, request, redirect, url_for, session
import mysql.connector
import joblib


# =========================================================
# APP SETUP
# =========================================================

app = Flask(__name__)

app.secret_key = "jobguard-secret-key"


# =========================================================
# LOAD ML MODEL
# =========================================================

model = joblib.load("jobguard_model.pkl")

vectorizer = joblib.load(
    "jobguard_vectorizer.pkl"
)


# =========================================================
# MYSQL CONNECTION
# =========================================================

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="1006",
    database="jobguard"
)


# =========================================================
# DATABASE CHECK
# =========================================================

def check_database():

    try:

        if not db.is_connected():

            db.reconnect(
                attempts=3,
                delay=2
            )

        return True

    except mysql.connector.Error:

        return False


# =========================================================
# RISK CALCULATION
# =========================================================

def calculate_risk(
    job_title,
    description,
    salary,
    experience,
    contact,
    job_url
):

    text = (
        str(job_title) + " " +
        str(description) + " " +
        str(salary) + " " +
        str(experience) + " " +
        str(contact) + " " +
        str(job_url)
    ).lower()


    # ML RISK

    ml_vector = vectorizer.transform(
        [text]
    )

    ml_probability = model.predict_proba(
        ml_vector
    )[0][1]

    ml_risk = int(
        ml_probability * 40
    )

    risk = ml_risk

    reasons = []


    # PAYMENT

    if (
        "registration fee" in text
        or "registration fees" in text
    ):

        risk += 25

        reasons.append(
            "Registration or upfront payment requirement detected."
        )


    if (
        "processing fee" in text
        or "pay fee" in text
        or "application fee" in text
    ):

        risk += 25

        reasons.append(
            "Payment requirement detected."
        )


    # WHATSAPP

    if "whatsapp" in text:

        risk += 15

        reasons.append(
            "WhatsApp-based job communication detected."
        )


    # TELEGRAM

    if "telegram" in text:

        risk += 15

        reasons.append(
            "Telegram-based job communication detected."
        )


    # SHORT URL

    if (
        "bit.ly" in text
        or "tinyurl" in text
        or "t.co" in text
    ):

        risk += 10

        reasons.append(
            "Shortened URL detected."
        )


    # GUARANTEED INCOME

    if (
        "guaranteed income" in text
        or "guaranteed salary" in text
    ):

        risk += 15

        reasons.append(
            "Guaranteed income or salary claim detected."
        )


    # HIGH EARNING

    if (
        "earn 1 lakh" in text
        or "1 lakh/month" in text
        or "earn ₹1 lakh" in text
    ):

        risk += 15

        reasons.append(
            "Unusually high earning claim detected."
        )


    # NO EXPERIENCE + HIGH INCOME

    if (
        "no experience" in text
        and (
            "high salary" in text
            or "1 lakh" in text
            or "1.5 lakh" in text
            or "2 lakh" in text
            or "guaranteed income" in text
        )
    ):

        risk += 20

        reasons.append(
            "High income claim combined with no experience requirement."
        )


    # LOW ELIGIBILITY

    if (
        "anyone can apply" in text
        and "no qualification" in text
    ):

        risk += 10

        reasons.append(
            "Unusually low eligibility requirement detected."
        )


    # OFFICIAL CAREERS SIGNAL

    if (
        "official company" in text
        or "careers page" in text
        or "/careers" in text
    ):

        risk -= 10


    # EMAIL SIGNAL

    if (
        "@" in str(contact)
        and "whatsapp" not in str(contact).lower()
        and "telegram" not in str(contact).lower()
    ):

        risk -= 5


    # LIMIT RISK

    if risk < 0:

        risk = 0


    if risk > 100:

        risk = 100


    # STATUS

    if risk >= 60:

        status = "Potentially Suspicious"

    elif risk >= 30:

        status = "Needs Verification"

    else:

        status = "Lower Risk"


    return risk, status, reasons


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    return render_template(
        "index.html"
    )


# =========================================================
# ANALYZE PAGE
# =========================================================

@app.route("/analyze")
def analyze():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )


    return render_template(
        "analyze.html"
    )


# =========================================================
# ANALYZE JOB
# =========================================================

@app.route(
    "/analyze-job",
    methods=["POST"]
)
def analyze_job():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )


    job_title = request.form.get(
        "job_title",
        ""
    ).strip()

    company = request.form.get(
        "company",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()

    salary = request.form.get(
        "salary",
        ""
    ).strip()

    experience = request.form.get(
        "experience",
        ""
    ).strip()

    location = request.form.get(
        "location",
        ""
    ).strip()

    contact = request.form.get(
        "contact",
        ""
    ).strip()

    job_url = request.form.get(
        "url",
        ""
    ).strip()


    if (
        not job_title
        or not company
        or not description
    ):

        return (
            "Job title, company and description are required.",
            400
        )


    risk, status, reasons = calculate_risk(
        job_title,
        description,
        salary,
        experience,
        contact,
        job_url
    )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor()


    try:

        sql = """
        INSERT INTO jobs
        (
            user_id,
            job_title,
            company,
            description,
            salary,
            experience,
            location,
            contact,
            job_url,
            risk_score,
            risk_status
        )
        VALUES
        (
            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
        )
        """


        values = (
            session["user_id"],
            job_title,
            company,
            description,
            salary,
            experience,
            location,
            contact,
            job_url,
            risk,
            status
        )


        cursor.execute(
            sql,
            values
        )

        db.commit()

        job_id = cursor.lastrowid


    except mysql.connector.Error:

        db.rollback()

        cursor.close()

        return (
            "Unable to save job to database.",
            500
        )


    cursor.close()


    return redirect(
        url_for(
            "result",
            job_id=job_id
        )
    )


# =========================================================
# RESULT
# =========================================================

@app.route("/result")
def result():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )


    job_id = request.args.get(
        "job_id",
        type=int
    )


    if not job_id:

        return (
            "Job ID missing.",
            400
        )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor(
        dictionary=True
    )


    cursor.execute(
        """
        SELECT *
        FROM jobs
        WHERE id=%s
        AND user_id=%s
        """,
        (
            job_id,
            session["user_id"]
        )
    )


    job = cursor.fetchone()

    cursor.close()


    if not job:

        return (
            "Job not found.",
            404
        )


    _, _, reasons = calculate_risk(
        job["job_title"],
        job["description"],
        job["salary"] or "",
        job["experience"] or "",
        job["contact"] or "",
        job["job_url"] or ""
    )


    return render_template(
        "result.html",
        job=job,
        reasons=reasons
    )


# =========================================================
# HISTORY
# =========================================================

@app.route("/history")
def history():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor(
        dictionary=True
    )


    cursor.execute(
        """
        SELECT
            id,
            job_title,
            company,
            risk_score,
            risk_status,
            created_at
        FROM jobs
        WHERE user_id=%s
        ORDER BY id DESC
        """,
        (
            session["user_id"],
        )
    )


    jobs = cursor.fetchall()

    cursor.close()


    return render_template(
        "history.html",
        jobs=jobs
    )


# =========================================================
# DETAILS
# =========================================================

@app.route("/details")
def details():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )


    job_id = request.args.get(
        "job_id",
        type=int
    )


    if not job_id:

        return (
            "Job ID missing.",
            400
        )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor(
        dictionary=True
    )


    cursor.execute(
        """
        SELECT *
        FROM jobs
        WHERE id=%s
        AND user_id=%s
        """,
        (
            job_id,
            session["user_id"]
        )
    )


    job = cursor.fetchone()

    cursor.close()


    if not job:

        return (
            "Job not found.",
            404
        )


    _, _, reasons = calculate_risk(
        job["job_title"],
        job["description"],
        job["salary"] or "",
        job["experience"] or "",
        job["contact"] or "",
        job["job_url"] or ""
    )


    return render_template(
        "details.html",
        job=job,
        reasons=reasons
    )


# =========================================================
# REPORT PAGE
# =========================================================

@app.route("/report")
def report():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )


    return render_template(
        "report.html"
    )


# =========================================================
# SUBMIT REPORT
# =========================================================

@app.route(
    "/submit-report",
    methods=["POST"]
)
def submit_report():

    if not session.get(
        "user_logged_in"
    ):

        return redirect(
            url_for("login")
        )


    job_title = request.form.get(
        "job_title",
        ""
    ).strip()

    company = request.form.get(
        "company",
        ""
    ).strip()

    job_url = request.form.get(
        "job_url",
        ""
    ).strip()

    reason = request.form.get(
        "reason",
        ""
    ).strip()

    description = request.form.get(
        "description",
        ""
    ).strip()


    if (
        not job_title
        or not company
        or not reason
    ):

        return (
            "Please fill all required fields.",
            400
        )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO reports
            (
                user_id,
                job_title,
                company,
                reason,
                description,
                job_url,
                report_status
            )
            VALUES
            (
                %s,%s,%s,%s,%s,%s,%s
            )
            """,
            (
                session["user_id"],
                job_title,
                company,
                reason,
                description,
                job_url,
                "Pending"
            )
        )


        db.commit()


    except mysql.connector.Error:

        db.rollback()

        cursor.close()

        return (
            "Unable to submit report.",
            500
        )


    cursor.close()


    return """
    <h2>Report submitted successfully.</h2>

    <br>

    <a href="/">
        Go to Home
    </a>
    """


# =========================================================
# SAFETY
# =========================================================

@app.route("/safety")
def safety():

    return render_template(
        "safety.html"
    )


# =========================================================
# ABOUT
# =========================================================

@app.route("/about")
def about():

    return render_template(
        "about.html"
    )


# =========================================================
# SIGNUP PAGE
# =========================================================

@app.route("/signup")
def signup():

    return render_template(
        "signup.html"
    )


# =========================================================
# CREATE USER ACCOUNT
# =========================================================

@app.route(
    "/signup-user",
    methods=["POST"]
)
def signup_user():

    full_name = request.form.get(
        "full_name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    ).strip()

    confirm_password = request.form.get(
        "confirm_password",
        ""
    ).strip()


    if (
        not full_name
        or not email
        or not password
    ):

        return (
            "Please fill all required fields.",
            400
        )


    if password != confirm_password:

        return (
            "Passwords do not match.",
            400
        )


    if len(password) < 6:

        return (
            "Password must contain at least 6 characters.",
            400
        )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO users
            (
                full_name,
                email,
                password
            )
            VALUES
            (
                %s,%s,%s
            )
            """,
            (
                full_name,
                email,
                password
            )
        )


        db.commit()


    except mysql.connector.Error as error:

        db.rollback()

        cursor.close()


        if error.errno == 1062:

            return (
                "Email already exists. Please use another email.",
                400
            )


        return (
            "Unable to create account.",
            500
        )


    cursor.close()


    return redirect(
        url_for("login")
    )


# =========================================================
# USER LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        ).strip()


        if not email or not password:

            return render_template(
                "login.html",
                error="Please enter email and password."
            )


        if not check_database():

            return render_template(
                "login.html",
                error="Database connection error."
            )


        cursor = db.cursor(
            dictionary=True
        )


        try:

            cursor.execute(
                """
                SELECT
                    id,
                    full_name,
                    email,
                    password
                FROM users
                WHERE LOWER(TRIM(email)) =
                      LOWER(TRIM(%s))
                """,
                (
                    email,
                )
            )


            user = cursor.fetchone()


        except mysql.connector.Error:

            cursor.close()

            return render_template(
                "login.html",
                error="Database error."
            )


        cursor.close()


        # EMAIL NOT FOUND

        if not user:

            return render_template(
                "login.html",
                error="Email not registered."
            )


        # PASSWORD CHECK

        database_password = str(
            user["password"]
        ).strip()


        if database_password != password:

            return render_template(
                "login.html",
                error="Invalid password."
            )


        # LOGIN SUCCESS

        session["user_logged_in"] = True

        session["user_id"] = user["id"]

        session["user_name"] = user["full_name"]

        session["user_email"] = user["email"]


        return redirect(
            url_for("analyze")
        )


    return render_template(
        "login.html"
    )


# =========================================================
# USER LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.pop(
        "user_logged_in",
        None
    )

    session.pop(
        "user_id",
        None
    )

    session.pop(
        "user_name",
        None
    )

    session.pop(
        "user_email",
        None
    )


    return redirect(
        url_for("home")
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        ).strip()


        ADMIN_USERNAME = "admin"

        ADMIN_PASSWORD = "admin123"


        if (
            username == ADMIN_USERNAME
            and password == ADMIN_PASSWORD
        ):

            session["admin_logged_in"] = True

            return redirect(
                url_for("admin_dashboard")
            )


        return render_template(
            "admin_login.html",
            error="Invalid username or password."
        )


    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
def admin_dashboard():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("admin_login")
        )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor(
        dictionary=True
    )


    cursor.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY id DESC
        """
    )

    jobs = cursor.fetchall()


    cursor.execute(
        """
        SELECT *
        FROM reports
        ORDER BY id DESC
        """
    )

    reports = cursor.fetchall()


    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM jobs
        """
    )

    total_jobs = cursor.fetchone()["total"]


    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM jobs
        WHERE risk_status='Potentially Suspicious'
        """
    )

    suspicious_jobs = cursor.fetchone()["total"]


    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM jobs
        WHERE risk_status='Needs Verification'
        """
    )

    verification_jobs = cursor.fetchone()["total"]


    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM reports
        """
    )

    total_reports = cursor.fetchone()["total"]


    cursor.close()


    return render_template(
        "admin_dashboard.html",
        jobs=jobs,
        reports=reports,
        total_jobs=total_jobs,
        suspicious_jobs=suspicious_jobs,
        verification_jobs=verification_jobs,
        total_reports=total_reports
    )


# =========================================================
# ADMIN DATASET
# =========================================================

@app.route("/admin/dataset")
def admin_dataset():

    if not session.get(
        "admin_logged_in"
    ):

        return redirect(
            url_for("admin_login")
        )


    if not check_database():

        return (
            "Database connection error.",
            500
        )


    cursor = db.cursor(
        dictionary=True
    )


    cursor.execute(
        """
        SELECT *
        FROM jobs
        ORDER BY id DESC
        """
    )


    jobs = cursor.fetchall()

    cursor.close()


    return render_template(
        "admin_dataset.html",
        jobs=jobs
    )


# =========================================================
# ADMIN LOGOUT
# =========================================================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_logged_in",
        None
    )


    return redirect(
        url_for("admin_login")
    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    app.run(
        debug=True
    )