from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired
import json

import numpy as np

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_encryption_key'

# Mock database of active attendees loaded dynamically from face_names.npy
try:
    raw_names = np.load('face_names.npy', allow_pickle=True)
    # Extract unique names and filter out UNKNOWN values
    active_attendees = sorted(list(set(str(name) for name in raw_names if str(name).upper() != "UNKNOWN")))
except Exception as e:
    print(f"Error loading face_names.npy: {e}")
    active_attendees = ["Arpan", "Jatin"]

# Conditional imports of ML/CV libraries for proper face recognition
REAL_FACE_RECOGNITION_AVAILABLE = False
live_detector = None
try:
    import cv2
    import torch
    import pandas as pd
    from live import Live
    REAL_FACE_RECOGNITION_AVAILABLE = True
    print("Proper face recognition dependencies are loaded successfully!")
except ImportError as e:
    print(f"Proper face recognition dependencies not available, running in Mock mode. (Error: {e})")



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
    global live_detector
    data = request.get_json() or {}
    period = data.get('period', 1)
    teacher_name = session.get('user', 'Teacher')
    
    if REAL_FACE_RECOGNITION_AVAILABLE:
        import threading
        live_detector = Live()
        
        def run_camera_thread():
            try:
                # Automate Excel workbook/sheet verification and creation
                excel_file = 'static/attendance_sheet.xlsx'
                import pandas as pd
                import os
                
                sheets = []
                if os.path.exists(excel_file):
                    try:
                        with pd.ExcelFile(excel_file) as xls:
                            sheets = xls.sheet_names
                    except Exception:
                        pass
                
                if teacher_name not in sheets:
                    df_new = pd.DataFrame(columns=["Roll No", "Name"])
                    try:
                        raw_names = np.load('face_names.npy', allow_pickle=True)
                        unique_names = sorted(list(set(str(name) for name in raw_names if str(name).upper() != "UNKNOWN")))
                        for idx, name in enumerate(unique_names):
                            df_new.loc[idx] = [101 + idx, name]
                    except Exception:
                        df_new.loc[0] = [101, "Arpan"]
                        df_new.loc[1] = [102, "Jatin"]
                    
                    if os.path.exists(excel_file):
                        with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                            df_new.to_excel(writer, sheet_name=teacher_name, index=False)
                    else:
                        with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                            df_new.to_excel(writer, sheet_name=teacher_name, index=False)
                
                # Start the physical face recognition engine loop
                live_detector.run(sheet_name=teacher_name, period=period)
            except Exception as e:
                print(f"Error running physical camera: {e}")
                
        threading.Thread(target=run_camera_thread, daemon=True).start()
        return jsonify({"message": f"📷 Live face recognition camera started for Period {period}!"})
    else:
        # Graceful cloud mock mode fallback
        import threading
        import time
        def mock_simulation():
            global active_attendees
            active_attendees = []
            time.sleep(3)
            active_attendees.append("Arpan")
            time.sleep(3)
            active_attendees.append("Jatin")
            
        threading.Thread(target=mock_simulation, daemon=True).start()
        return jsonify({"message": f"📷 Mock Camera initiated for Period {period} (running in fallback mode)!"})

@app.route('/attendance_data')
def attendance_data():
    # Dynamically polled by the camera page every 5 seconds
    if REAL_FACE_RECOGNITION_AVAILABLE and live_detector is not None:
        return jsonify({"names": live_detector.detected_names})
    return jsonify({"names": active_attendees})


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

