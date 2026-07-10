from flask import Flask, render_template, jsonify, redirect, send_file, url_for, session, request
from flask_bootstrap import Bootstrap5
import threading
import io
import pandas as pd
from live import Live
from mail import Mail, Download
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired


app = Flask(__name__)
Bootstrap5(app)

app.config['SECRET_KEY'] = 'RORONOA'


class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///teacher.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Teacher(db.Model):
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


live = Live()


class Loginform(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


@app.route('/')
def home():
    return render_template("home.html")


@app.route('/login', methods=['GET', 'POST'])
def login():
    result = None
    form = Loginform()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = Teacher.query.filter_by(username=username).first()

        if user and user.password == password:
            session['logged_in'] = True
            session['username'] = username
            result = "success"
        else:
            result = "Invalid username or password."

        form.username.data = ''
        form.password.data = ''

    return render_template("index1.html", result=result, form=form)


@app.route('/welcome')
def welcome():
    uname = session.get('username')
    teacher = Teacher.query.filter_by(username=uname).first()
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template("welcome.html", key=teacher.name)


@app.route('/action')
def act():
    return render_template("action.html")


@app.route('/video_feed')
def video_feed():
    return render_template("attendance.html")


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/attendance_data')
def attendance_data():
    return live.get_attendance_data()


@app.route('/start_camera', methods=['POST'])
def start_camera_api():
    info = request.get_json()
    period = info.get('period')
    uname = session.get('username')
    threading.Thread(target=start_camera, args=(uname, period)).start()
    return jsonify({"message": "Camera started."})


@app.route('/data')
def data():
    return render_template("data.html")


@app.route('/display')
def display():
    uname = session.get('username')
    subject = request.args.get('subject')
    sheet = subject or uname
    sub = Teacher.query.filter_by(username=sheet).first()
    df = pd.read_excel("static/attendance_sheet.xlsx", sheet_name=sheet)
    info = df.to_dict(orient='records')
    columns = df.columns.tolist()
    return render_template('display2.html', key=sub.password, data=info, columns=columns)


@app.route('/download')
def download():
    uname = session.get('username')
    df = pd.read_excel("static/attendance_sheet.xlsx", sheet_name=uname)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    output.seek(0)
    return send_file(output, download_name='attendance.xlsx', as_attachment=True)


@app.route('/student_login')
def student_login():
    return render_template("welcome2.html")


def start_camera(sheet_name, period):
    live.run(sheet_name, period)
    # mail = Mail()
    # mail.send(sheet_name)


if __name__ == '__main__':
    app.run(debug=True)
