from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

# Initialize Flask app and SQLAlchemy
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teachers.db'
db = SQLAlchemy(app)

class Teacher(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(50), nullable=False)
    subject: Mapped[str] = mapped_column(String(100), nullable=True)

# Initialize the database and create tables
with app.app_context():
    db.create_all()



with app.app_context():
    with app.app_context():
        teachers = Teacher.query.all()

        for teacher in teachers:
            if teacher.username == "sk_sir":
                teacher.subject = "Object Oriented System Design"
            elif teacher.username == "hr_sir":
                teacher.subject = "Computer Organisation and Architecture"
            elif teacher.username == "spm_sir":
                teacher.subject = "Communication System"
            elif teacher.username == "bs_sir":
                teacher.subject = "Graphics"
            else:
                teacher.subject = "Formal Language and Automata Theory"  # Default subject

        db.session.commit()

    db.session.commit()

with app.app_context():
    teachers = Teacher.query.all()

    for teacher in teachers:
        teacher.subject = "Science"

    db.session.commit()

if __name__ == '__main__':
    app.run(debug=True)
