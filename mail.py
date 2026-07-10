import smtplib
import pandas as pd
import io


class Download:
    def __init__(self, sheetname):
        df = pd.read_excel("static/attendance_sheet.xlsx", sheet_name=sheetname)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Sheet1')
        output.seek(0)


class Mail:
    def __init__(self):
        self.sender_email = "a68081169@gmail.com"
        self.sender_password = "xktl jehz kjzz tznx"
        self.sheet_path = "static/attendance_sheet.xlsx"
        self.connect = smtplib.SMTP("smtp.gmail.com", 587)
        self.connect.starttls()
        self.connect.login(user=self.sender_email, password=self.sender_password)

    def send(self, sheet_name):
        df = pd.read_excel(self.sheet_path, sheet_name=sheet_name)
        last_column = df.columns[-1]
        for index, row in df.iterrows():
            if row[last_column] == 0:
                subject = "Attendance Alert"
                body = (
                    "Hey, you were absent in class today.\n"
                    "What are you doing in your life?\n"
                    "Please attend classes regularly!"
                )
                message = f"Subject: {subject}\n\n{body}"
                self.connect.sendmail(from_addr=self.sender_email, to_addrs=row["Mail"], msg=message)

        self.connect.close()


