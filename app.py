from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_encryption_key'

# Mock database of active attendees
active_attendees = ["John Doe", "Jane Smith"]

# 1. WTForm definition for Teacher Login (index1.html)
class TeacherLoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

# --- ROUTING PATHS ---

@app.route('/')
def index():
    # Role Selection Page
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    # Teacher login processing
    form = TeacherLoginForm()
    result = None
    if form.validate_on_submit():
        if form.username.data == "admin" and form.password.data == "password":
            session['user'] = form.username.data
            return render_template('index1.html', form=form, result="success")
        else:
            result = "Invalid credentials. Please try again."
    return render_template('index1.html', form=form, result=result)


@app.route('/student_login', methods=['GET', 'POST'])
def student_login():
    # Handles student entry (welcome2.html / attendance.html)
    if request.method == 'POST':
        # Simple placeholder verification
        session['user'] = request.form.get('username')
        return redirect(url_for('welcome2'))
    return render_template('attendance.html')

@app.route('/video_feed')
def video_feed():
    return render_template('attendance.html')


@app.route('/welcome')
def welcome():
    user = session.get('user', 'Teacher')
    return render_template('welcome.html', key=user)

@app.route('/welcome2')
def welcome2():
    return render_template('welcome2.html')

@app.route('/action')
def action():
    return render_template('action.html')

@app.route('/data')
def data_menu():
    return render_template('data.html')

@app.route('/display')
def display_records():
    subject = request.args.get('subject', 'Unknown Subject')
    # Mock data grid structure
    columns = ["Roll No", "Student Name", "Status"]
    mock_data = [
        {"Roll No": "101", "Student Name": "Alice", "Status": "Present"},
        {"Roll No": "102", "Student Name": "Bob", "Status": "Absent"}
    ]
    return render_template('display2.html', key=subject, columns=columns, data=mock_data)

# --- API ENDPOINTS FOR THE CAMERA INTERFACE ---

@app.route('/start_camera', methods=['POST'])
def start_camera():
    data = request.get_json()
    period = data.get('period')
    # Logic to trigger physical hardware webcam script goes here
    return jsonify({"message": f"📷 Camera initiated successfully for Period {period}!"})

@app.route('/attendance_data')
def attendance_data():
    # Dynamically polled by the camera page every 5 seconds
    return jsonify({"names": active_attendees})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)