
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# --------------------------------
# STUDENT USER TABLE
# --------------------------------

class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100), nullable=False)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    email = db.Column(
        db.String(120),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    # One student can have many predictions
    predictions = db.relationship(
        "Prediction",
        backref="student",
        lazy=True
    )


# --------------------------------
# ADMIN TABLE
# --------------------------------

class Admin(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(50),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )


# --------------------------------
# STUDENT PREDICTION TABLE
# --------------------------------

class Prediction(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    study_hours = db.Column(db.Float)

    attendance = db.Column(db.Float)

    previous_score = db.Column(db.Float)

    assignment_score = db.Column(db.Float)

    sleep_hours = db.Column(db.Float)

    predicted_score = db.Column(db.Float)

    category = db.Column(db.String(50))

    # Connect each prediction to its student
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=True
    )
