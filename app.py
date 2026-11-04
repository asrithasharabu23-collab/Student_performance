from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, make_response
)

from functools import wraps
from io import BytesIO
from datetime import datetime

import pandas as pd
import joblib

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from database import db, User, Admin, Prediction

# PDF imports
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet


# ==========================================
# 1. FLASK CONFIGURATION
# ==========================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "student-performance-project-secret-key"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///predictions.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ==========================================
# 2. CREATE AND UPDATE DATABASE
# ==========================================

with app.app_context():

    db.create_all()

    # Check whether the prediction table exists
    inspector = inspect(db.engine)

    if inspector.has_table("prediction"):

        columns = [
            column["name"]
            for column in inspector.get_columns("prediction")
        ]

        if "user_id" not in columns:

            with db.engine.begin() as connection:

                connection.execute(
                    text(
                        "ALTER TABLE prediction "
                        "ADD COLUMN user_id INTEGER REFERENCES user(id)"
                    )
                )

            print("Database updated successfully.")


# ==========================================
# 3. LOAD MACHINE LEARNING MODEL
# ==========================================

model = joblib.load("student_model.pkl")


# ==========================================
# 4. STUDENT LOGIN DECORATOR
# ==========================================

def login_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:

            flash("Please login to continue.", "error")

            return redirect(url_for("login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# 5. ADMIN LOGIN DECORATOR
# ==========================================

def admin_required(function):

    @wraps(function)
    def wrapper(*args, **kwargs):

        if "admin_id" not in session:

            flash("Please login as admin first.", "error")

            return redirect(url_for("admin_login"))

        return function(*args, **kwargs)

    return wrapper


# ==========================================
# 6. STUDENT REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if "user_id" in session:

        return redirect(url_for("home"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        username = request.form.get(
            "username", ""
        ).strip().lower()

        email = request.form.get(
            "email", ""
        ).strip().lower()

        password = request.form.get("password", "")

        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not name or not username or not email or not password:

            flash("Please fill in all fields.", "error")

            return redirect(url_for("register"))

        if len(username) < 3:

            flash(
                "Username must contain at least 3 characters.",
                "error"
            )

            return redirect(url_for("register"))

        if "@" not in email or "." not in email.split("@")[-1]:

            flash("Please enter a valid email address.", "error")

            return redirect(url_for("register"))

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "error"
            )

            return redirect(url_for("register"))

        if password != confirm_password:

            flash("Passwords do not match.", "error")

            return redirect(url_for("register"))

        existing_user = User.query.filter(
            (User.username == username) |
            (User.email == email)
        ).first()

        if existing_user:

            if existing_user.username == username:

                flash(
                    "Username already exists. Choose another.",
                    "error"
                )

            else:

                flash(
                    "Email already registered. Please login.",
                    "error"
                )

            return redirect(url_for("register"))

        try:

            hashed_password = generate_password_hash(password)

            new_user = User(
                name=name,
                username=username,
                email=email,
                password=hashed_password
            )

            db.session.add(new_user)

            db.session.commit()

            flash(
                "Registration successful! Please login.",
                "success"
            )

            return redirect(url_for("login"))

        except SQLAlchemyError:

            db.session.rollback()

            flash(
                "Registration failed. Please try again.",
                "error"
            )

    return render_template("register.html")


# ==========================================
# 7. STUDENT LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if "user_id" in session:

        return redirect(url_for("home"))

    if request.method == "POST":

        login_id = request.form.get(
            "login_id", ""
        ).strip().lower()

        password = request.form.get("password", "")

        user = User.query.filter(
            (User.email == login_id) |
            (User.username == login_id)
        ).first()

        if user and check_password_hash(user.password, password):

            session.clear()

            session["user_id"] = user.id

            session["student_name"] = user.name

            flash("Login successful!", "success")

            return redirect(url_for("home"))

        flash(
            "Invalid email/username or password.",
            "error"
        )

    return render_template("login.html")


# ==========================================
# 8. STUDENT LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have logged out successfully.",
        "success"
    )

    return redirect(url_for("login"))


# ==========================================
# 9. ADMIN LOGIN
# ==========================================

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():

    if "admin_id" in session:

        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get("password", "")

        admin = Admin.query.filter_by(
            username=username
        ).first()

        if admin and check_password_hash(admin.password, password):

            session.clear()

            session["admin_id"] = admin.id

            session["admin_username"] = admin.username

            flash(
                "Admin login successful!",
                "success"
            )

            return redirect(url_for("admin_dashboard"))

        flash(
            "Invalid admin username or password.",
            "error"
        )

    return render_template("admin_login.html")


# ==========================================
# 10. ADMIN DASHBOARD
# ==========================================

@app.route("/admin-dashboard")
@admin_required
def admin_dashboard():

    search = request.args.get(
        "search", ""
    ).strip()

    # Get all registered students
    student_query = User.query

    if search:

        student_query = student_query.filter(
            (User.name.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )

    students = student_query.order_by(
        User.id.desc()
    ).all()

    # Get all predictions
    predictions = Prediction.query.order_by(
        Prediction.id.desc()
    ).all()

    total_students = User.query.count()

    total_predictions = Prediction.query.count()

    return render_template(
        "admin_dashboard.html",
        students=students,
        predictions=predictions,
        total_students=total_students,
        total_predictions=total_predictions,
        search=search
    )


# ==========================================
# 11. ADMIN LOGOUT
# ==========================================

@app.route("/admin-logout")
@admin_required
def admin_logout():

    session.clear()

    flash(
        "Admin logged out successfully.",
        "success"
    )

    return redirect(url_for("admin_login"))


# ==========================================
# 12. HOME PAGE - STUDENT PREDICTION
# ==========================================

@app.route("/", methods=["GET", "POST"])
@login_required
def home():

    prediction = None
    category = None
    suggestion = None
    insights = []
    error = None

    latest_prediction_id = None

    if request.method == "POST":

        try:

            study_hours = float(
                request.form["study_hours"]
            )

            attendance = float(
                request.form["attendance"]
            )

            previous_score = float(
                request.form["previous_score"]
            )

            assignment_score = float(
                request.form["assignment_score"]
            )

            sleep_hours = float(
                request.form["sleep_hours"]
            )

            # Validate inputs

            if not 0 <= study_hours <= 24:

                raise ValueError(
                    "Study hours must be between 0 and 24."
                )

            if not 0 <= attendance <= 100:

                raise ValueError(
                    "Attendance must be between 0 and 100."
                )

            if not 0 <= previous_score <= 100:

                raise ValueError(
                    "Previous marks must be between 0 and 100."
                )

            if not 0 <= assignment_score <= 100:

                raise ValueError(
                    "Assignment marks must be between 0 and 100."
                )

            if not 0 <= sleep_hours <= 24:

                raise ValueError(
                    "Sleep hours must be between 0 and 24."
                )

            # Prepare input for ML model

            student_data = pd.DataFrame([{

                "study_hours": study_hours,

                "attendance": attendance,

                "previous_score": previous_score,

                "assignment_score": assignment_score,

                "sleep_hours": sleep_hours

            }])

            # Predict marks

            result = model.predict(student_data)[0]

            prediction = round(
                max(0, min(100, float(result))),
                2
            )

            # Performance category

            if prediction >= 85:

                category = "Excellent"

                suggestion = (
                    "Excellent performance! "
                    "Maintain your study routine."
                )

            elif prediction >= 70:

                category = "Good"

                suggestion = (
                    "Good performance! "
                    "Continue practicing and revising."
                )

            elif prediction >= 50:

                category = "Average"

                suggestion = (
                    "Improve your preparation "
                    "by studying consistently."
                )

            else:

                category = "Needs Improvement"

                suggestion = (
                    "Follow a daily study plan "
                    "and focus on weak subjects."
                )

            # Student insights

            if study_hours < 3:

                insights.append(
                    "Study for at least 3 hours daily."
                )

            if attendance < 75:

                insights.append(
                    "Improve your attendance to at least 75%."
                )

            if previous_score < 50:

                insights.append(
                    "Revise previous topics and strengthen your basics."
                )

            if assignment_score < 50:

                insights.append(
                    "Complete assignments regularly and practice more."
                )

            if sleep_hours < 6:

                insights.append(
                    "Try to maintain a healthy sleep routine."
                )

            if not insights:

                insights.append(
                    "Your study habits look good. "
                    "Keep up the consistency!"
                )

            # Save prediction in database

            new_prediction = Prediction(

                study_hours=study_hours,

                attendance=attendance,

                previous_score=previous_score,

                assignment_score=assignment_score,

                sleep_hours=sleep_hours,

                predicted_score=prediction,

                category=category,

                user_id=session["user_id"]

            )

            db.session.add(new_prediction)

            db.session.commit()

            latest_prediction_id = new_prediction.id

        except (ValueError, TypeError) as e:

            db.session.rollback()

            error = str(e)

        except SQLAlchemyError:

            db.session.rollback()

            error = (
                "Unable to save prediction. Please try again."
            )

    return render_template(

        "index.html",

        prediction=prediction,

        category=category,

        suggestion=suggestion,

        insights=insights,

        error=error,

        student_name=session.get("student_name"),

        latest_prediction_id=latest_prediction_id

    )


# ==========================================
# 13. VIEW, SEARCH AND FILTER HISTORY
# ==========================================

@app.route("/history")
@login_required
def history():

    search = request.args.get(
        "search", ""
    ).strip()

    category_filter = request.args.get(
        "category", ""
    ).strip()

    query = Prediction.query.filter_by(
        user_id=session["user_id"]
    )

    if search:

        if search.isdigit():

            query = query.filter(
                Prediction.id == int(search)
            )

        else:

            query = query.filter(
                Prediction.category.ilike(
                    f"%{search}%"
                )
            )

    if category_filter:

        query = query.filter(
            Prediction.category == category_filter
        )

    records = query.order_by(
        Prediction.id.desc()
    ).all()

    return render_template(

        "history.html",

        records=records,

        search=search,

        category_filter=category_filter

    )


# ==========================================
# 14. DELETE PREDICTION
# ==========================================

@app.route(
    "/delete/<int:prediction_id>",
    methods=["POST"]
)
@login_required
def delete_prediction(prediction_id):

    record = Prediction.query.filter_by(

        id=prediction_id,

        user_id=session["user_id"]

    ).first()

    if record:

        try:

            db.session.delete(record)

            db.session.commit()

            flash(
                "Prediction record deleted successfully.",
                "success"
            )

        except SQLAlchemyError:

            db.session.rollback()

            flash(
                "Unable to delete prediction.",
                "error"
            )

    else:

        flash(
            "Prediction record not found.",
            "error"
        )

    return redirect(url_for("history"))


# ==========================================
# 15. STUDENT DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    records = Prediction.query.filter_by(

        user_id=session["user_id"]

    ).order_by(

        Prediction.id.asc()

    ).all()

    total_predictions = len(records)

    average_marks = "N/A"

    highest_marks = "N/A"

    average_study_hours = "N/A"

    category_labels = [

        "Excellent",

        "Good",

        "Average",

        "Needs Improvement"

    ]

    category_counts = [0, 0, 0, 0]

    study_hours_data = []

    predicted_marks_data = []

    attendance_data = []

    record_labels = []

    if total_predictions > 0:

        marks = [
            record.predicted_score
            for record in records
        ]

        hours = [
            record.study_hours
            for record in records
        ]

        attendance_values = [
            record.attendance
            for record in records
        ]

        average_marks = round(
            sum(marks) / total_predictions,
            2
        )

        highest_marks = round(
            max(marks),
            2
        )

        average_study_hours = round(
            sum(hours) / total_predictions,
            2
        )

        for record in records:

            if record.category in category_labels:

                index = category_labels.index(
                    record.category
                )

                category_counts[index] += 1

        study_hours_data = hours

        predicted_marks_data = marks

        attendance_data = attendance_values

        record_labels = [

            "Record " + str(record.id)

            for record in records

        ]

    return render_template(

        "dashboard.html",

        total_predictions=total_predictions,

        average_marks=average_marks,

        highest_marks=highest_marks,

        average_study_hours=average_study_hours,

        category_labels=category_labels,

        category_counts=category_counts,

        study_hours_data=study_hours_data,

        predicted_marks_data=predicted_marks_data,

        attendance_data=attendance_data,

        record_labels=record_labels

    )


# ==========================================
# 16. DOWNLOAD STUDENT PDF REPORT
# ==========================================

@app.route("/download-report/<int:prediction_id>")
@login_required
def download_report(prediction_id):

    # Get only the logged-in student's prediction

    record = Prediction.query.filter_by(

        id=prediction_id,

        user_id=session["user_id"]

    ).first_or_404()

    student = db.session.get(
        User,
        session["user_id"]
    )

    if student is None:

        return "Student account not found.", 404

    buffer = BytesIO()

    pdf = SimpleDocTemplate(

        buffer,

        pagesize=A4,

        rightMargin=40,

        leftMargin=40,

        topMargin=40,

        bottomMargin=40

    )

    styles = getSampleStyleSheet()

    content = []

    content.append(

        Paragraph(

            "Student Performance Prediction Report",

            styles["Title"]

        )

    )

    content.append(Spacer(1, 15))

    content.append(

        Paragraph(

            "Student Information",

            styles["Heading2"]

        )

    )

    content.append(Spacer(1, 10))

    student_data = [

        ["Student Name", student.name],

        ["Username", student.username],

        ["Email", student.email],

        [
            "Report Date",
            datetime.now().strftime("%d-%m-%Y %H:%M")
        ]

    ]

    student_table = Table(

        student_data,

        colWidths=[140, 350]

    )

    student_table.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0, 0),
            (0, -1),
            colors.lightblue
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey
        ),

        (
            "PADDING",
            (0, 0),
            (-1, -1),
            8
        )

    ]))

    content.append(student_table)

    content.append(Spacer(1, 25))

    content.append(

        Paragraph(

            "Academic Performance Details",

            styles["Heading2"]

        )

    )

    content.append(Spacer(1, 10))

    prediction_data = [

        ["Parameter", "Value"],

        ["Study Hours", str(record.study_hours)],

        ["Attendance", str(record.attendance) + "%"],

        ["Previous Exam Marks", str(record.previous_score)],

        ["Assignment Marks", str(record.assignment_score)],

        ["Sleep Hours", str(record.sleep_hours)],

        [
            "Predicted Marks",
            str(record.predicted_score) + " / 100"
        ],

        ["Performance Category", record.category]

    ]

    prediction_table = Table(

        prediction_data,

        colWidths=[240, 250]

    )

    prediction_table.setStyle(TableStyle([

        (
            "BACKGROUND",
            (0, 0),
            (-1, 0),
            colors.HexColor("#2455c3")
        ),

        (
            "TEXTCOLOR",
            (0, 0),
            (-1, 0),
            colors.white
        ),

        (
            "GRID",
            (0, 0),
            (-1, -1),
            0.5,
            colors.grey
        ),

        (
            "PADDING",
            (0, 0),
            (-1, -1),
            9
        ),

        (
            "FONTNAME",
            (0, 0),
            (-1, 0),
            "Helvetica-Bold"
        )

    ]))

    content.append(prediction_table)

    content.append(Spacer(1, 25))

    content.append(

        Paragraph(

            "Performance Suggestion",

            styles["Heading2"]

        )

    )

    suggestions = []

    if record.predicted_score >= 85:

        suggestions.append(
            "Excellent performance! Maintain your study routine."
        )

    elif record.predicted_score >= 70:

        suggestions.append(
            "Good performance! Continue practicing and revising."
        )

    elif record.predicted_score >= 50:

        suggestions.append(
            "Improve your preparation by studying consistently."
        )

    else:

        suggestions.append(
            "Follow a daily study plan and focus on weak subjects."
        )

    if record.study_hours < 3:

        suggestions.append(
            "Try studying for at least 3 hours daily."
        )

    if record.attendance < 75:

        suggestions.append(
            "Improve your attendance to at least 75%."
        )

    if record.previous_score < 50:

        suggestions.append(
            "Revise previous topics and strengthen your basics."
        )

    if record.assignment_score < 50:

        suggestions.append(
            "Complete assignments regularly."
        )

    if record.sleep_hours < 6:

        suggestions.append(
            "Try to maintain a healthy sleep routine."
        )

    for item in suggestions:

        content.append(

            Paragraph(
                "- " + item,
                styles["BodyText"]
            )

        )

        content.append(Spacer(1, 7))

    content.append(Spacer(1, 20))

    content.append(

        Paragraph(

            "Note: Predicted marks are estimates based on the "
            "machine learning model and are not guaranteed "
            "exam results.",

            styles["Italic"]

        )

    )

    # Generate PDF

    pdf.build(content)

    buffer.seek(0)

    response = make_response(
        buffer.getvalue()
    )

    response.headers["Content-Type"] = "application/pdf"

    response.headers["Content-Disposition"] = (
        f'attachment; filename="student_report_{record.id}.pdf"'
    )

    return response


# ==========================================
# 17. RUN FLASK APPLICATION
# ==========================================

if __name__ == "__main__":

    app.run(debug=True)