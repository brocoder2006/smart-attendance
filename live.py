import cv2
import numpy as np
from facenet_pytorch import MTCNN, InceptionResnetV1
import pandas as pd
from datetime import date
import json


class Live:
    def __init__(self, attendance_file='static/attendance_sheet.xlsx',
                 face_encodings='face_features.npy',
                 face_names='face_names.npy'):
        self.attendance_file = attendance_file
        self.face_encodings_file = face_encodings
        self.face_names_file = face_names
        self.detected_names = []

    def run(self, sheet_name, period):
        try:
            df = pd.read_excel(self.attendance_file, sheet_name=sheet_name)
        except ValueError:
            print(f"Sheet '{sheet_name}' not found in Excel file.")
            return

        today = date.today().strftime("%d-%m-%Y")
        if df.columns[-1] != today:
            df[today] = 0

        mtcnn = MTCNN(keep_all=True, thresholds=[0.6, 0.7, 0.7], device='cpu')
        resnet = InceptionResnetV1(pretrained='vggface2').eval()

        face_features = np.load(self.face_encodings_file).reshape(-1, 512)
        face_names = np.load(self.face_names_file)
        time = {name: 0 for name in face_names}

        capture = cv2.VideoCapture(0)

        while True:
            ret, frame = capture.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            boxes, _ = mtcnn.detect(frame_rgb)

            if boxes is not None:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box)
                    face_roi = frame_rgb[max(0, y1):min(frame.shape[0], y2), max(0, x1):min(frame.shape[1], x2)]

                    if face_roi.size == 0:
                        continue

                    try:
                        face_tensor = mtcnn(face_roi)
                        if face_tensor is not None:
                            if face_tensor.dim() == 5:
                                face_tensor = face_tensor.squeeze(0)
                            if face_tensor.dim() == 3:
                                face_tensor = face_tensor.unsqueeze(0)

                            embedding = resnet(face_tensor).detach().numpy().flatten()
                            distances = np.linalg.norm(face_features - embedding, axis=1)
                            min_index = np.argmin(distances)
                            min_distance = distances[min_index]

                            if min_distance < 0.8:
                                label = face_names[min_index]
                                time[label] += 1
                                color = (0, 255, 0)
                            else:
                                label = "UNKNOWN"
                                color = (0, 0, 255)

                            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                            cv2.putText(frame, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)
                    except Exception:
                        continue

            for person, time_spent in time.items():
                if time_spent >= 40:
                    df.loc[df['Name'] == person, today] = int(period)
                    if person not in self.detected_names:
                        self.detected_names.append(person)

            cv2.imshow('Face Recognition', frame)

            if cv2.waitKey(1) & 0xFF == ord('d'):
                break

        capture.release()
        cv2.destroyAllWindows()

        with pd.ExcelWriter(self.attendance_file, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name, index=False)

    def get_attendance_data(self):
        return json.dumps({"names": self.detected_names})
