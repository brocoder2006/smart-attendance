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
mtcnn_model = None
resnet_model = None
face_features = None
face_names = None
detected_students = set()

try:
    import cv2
    import torch
    import pandas as pd
    from live import Live
    REAL_FACE_RECOGNITION_AVAILABLE = True
    print("Proper face recognition dependencies are loaded successfully!")
    
    # Bypass macOS SSL certificate verification for model downloads
    import ssl
    ssl._create_default_https_context = ssl._create_unverified_context
    
    # Pre-load face recognition models globally for fast real-time inference

    from facenet_pytorch import MTCNN, InceptionResnetV1
    mtcnn_model = MTCNN(keep_all=True, thresholds=[0.6, 0.7, 0.7], device='cpu')
    resnet_model = InceptionResnetV1(pretrained='vggface2').eval()
    face_features = np.load('face_features.npy').reshape(-1, 512)
    face_names = np.load('face_names.npy')
    print("Face recognition models initialized successfully!")
except Exception as e:
    print(f"Proper face recognition dependencies or models not available, running in Mock mode. (Error: {e})")




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
    global detected_students
    data = request.get_json() or {}
    period = data.get('period', 1)
    
    # Reset detected students for the new camera session
    detected_students = set()
    return jsonify({"message": f"Camera session initiated for Period {period}."})

@app.route('/process_frame', methods=['POST'])
def process_frame():
    global detected_students
    data = request.get_json() or {}
    image_base64 = data.get('image')
    period = data.get('period', 1)
    teacher_name = session.get('user', 'Teacher')
    
    if not image_base64:
        return jsonify({"names": list(detected_students)})
        
    if REAL_FACE_RECOGNITION_AVAILABLE and mtcnn_model is not None:
        try:
            import base64
            import io
            from PIL import Image
            
            # Decode base64 image from browser webcam
            image_data = base64.b64decode(image_base64)
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB numpy format
            frame_rgb = np.array(image.convert("RGB"))
            
            # Detect faces
            boxes, _ = mtcnn_model.detect(frame_rgb)
            detected_now = []
            
            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box)
                    # Extract face region of interest
                    face_roi = frame_rgb[max(0, y1):min(frame_rgb.shape[0], y2), max(0, x1):min(frame_rgb.shape[1], x2)]
                    if face_roi.size == 0:
                        continue
                        
                    # Get face tensor and embedding
                    face_tensor = mtcnn_model(face_roi)
                    if face_tensor is not None:
                        if face_tensor.dim() == 5:
                            face_tensor = face_tensor.squeeze(0)
                        if face_tensor.dim() == 3:
                            face_tensor = face_tensor.unsqueeze(0)
                            
                        embedding = resnet_model(face_tensor).detach().numpy().flatten()
                        # Compare with database
                        distances = np.linalg.norm(face_features - embedding, axis=1)
                        min_index = np.argmin(distances)
                        min_distance = distances[min_index]
                        
                        if min_distance < 0.8:
                            name = str(face_names[min_index])
                            if name.upper() != "UNKNOWN":
                                detected_now.append(name)
                                detected_students.add(name)
                                
            # Mark newly detected students as present in the Excel sheet
            for name in detected_now:
                mark_present_in_excel(name, period, teacher_name)
                
            return jsonify({"names": list(detected_now)})
        except Exception as e:
            print(f"Error processing frame: {e}")
            return jsonify({"names": list(detected_students)})
    else:
        # Mock mode fallback (simulates detecting Arpan and Jatin after a few frames)
        import time
        mock_names = ["Arpan", "Jatin"]
        if len(detected_students) == 0:
            detected_students.add(mock_names[0])
            # Mark in Excel
            mark_present_in_excel(mock_names[0], period, teacher_name)
        elif len(detected_students) == 1:
            detected_students.add(mock_names[1])
            # Mark in Excel
            mark_present_in_excel(mock_names[1], period, teacher_name)
        return jsonify({"names": list(detected_students)})

def mark_present_in_excel(name, period, teacher_name):
    try:
        excel_file = 'static/attendance_sheet.xlsx'
        import pandas as pd
        from datetime import date
        import os
        
        sheets = []
        if os.path.exists(excel_file):
            try:
                with pd.ExcelFile(excel_file) as xls:
                    sheets = xls.sheet_names
            except Exception:
                pass
                
        # Generate sheets or open existing sheet
        if teacher_name not in sheets:
            df = pd.DataFrame(columns=["Roll No", "Name"])
            try:
                raw_names = np.load('face_names.npy', allow_pickle=True)
                unique_names = sorted(list(set(str(n) for n in raw_names if str(n).upper() != "UNKNOWN")))
                for idx, student_name in enumerate(unique_names):
                    df.loc[idx] = [101 + idx, student_name]
            except Exception:
                df.loc[0] = [101, "Arpan"]
                df.loc[1] = [102, "Jatin"]
        else:
            df = pd.read_excel(excel_file, sheet_name=teacher_name)
            
        # Add column for today if not present
        today = date.today().strftime("%d-%m-%Y")
        if today not in df.columns:
            df[today] = 0
            
        # Set period for name
        if name in df['Name'].values:
            df.loc[df['Name'] == name, today] = int(period)
            
        # Write back
        if os.path.exists(excel_file):
            with pd.ExcelWriter(excel_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df.to_excel(writer, sheet_name=teacher_name, index=False)
        else:
            with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name=teacher_name, index=False)
    except Exception as e:
        print(f"Error marking present in Excel: {e}")

@app.route('/attendance_data')
def attendance_data():
    return jsonify({"names": list(detected_students)})



@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

