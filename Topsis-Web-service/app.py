import os
import re
import smtplib
import pandas as pd
import numpy as np
from flask import Flask, request, render_template, flash
from werkzeug.utils import secure_filename
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Needed for flash messages
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# --- CONFIGURATION (CHANGE THESE) ---
SENDER_EMAIL = ""  # <--- REPLACE THIS
SENDER_PASSWORD = ""  # <--- REPLACE THIS (Not your login password)

def validate_email(email):
    regex = r'^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$'
    return re.search(regex, email)

def send_email(recipient_email, result_file_path):
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = "Your TOPSIS Analysis Result"

    body = "Hello,\n\nPlease find the attached result file for your TOPSIS analysis.\n\nBest Regards,\nTOPSIS Web Service"
    msg.attach(MIMEText(body, 'plain'))

    # Attachment
    attachment = open(result_file_path, "rb")
    part = MIMEBase('application', 'octet-stream')
    part.set_payload((attachment).read())
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(result_file_path)}")
    msg.attach(part)

    # Sending
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        text = msg.as_string()
        server.sendmail(SENDER_EMAIL, recipient_email, text)
        server.quit()
        return True
    except Exception as e:
        print(f"Email Error: {e}")
        return False

def run_topsis(file_path, weights, impacts):
    try:
        df = pd.read_csv(file_path)
        if df.shape[1] < 3:
            return None, "Input file must contain three or more columns."
        
        # Check numeric
        data = df.iloc[:, 1:].values
        if not np.issubdtype(data.dtype, np.number):
             # Try converting to numeric
             try:
                 data = df.iloc[:, 1:].astype(float).values
             except:
                 return None, "From 2nd column onwards, values must be numeric."

        # Validate counts
        num_cols = data.shape[1]
        if len(weights) != num_cols or len(impacts) != num_cols:
            return None, f"Weights ({len(weights)}), Impacts ({len(impacts)}), and Columns ({num_cols}) count mismatch."

        # Calculation
        norm_data = data / np.sqrt((data**2).sum(axis=0))
        weighted_data = norm_data * weights
        
        ideal_best = []
        ideal_worst = []
        for i in range(num_cols):
            if impacts[i] == '+':
                ideal_best.append(np.max(weighted_data[:, i]))
                ideal_worst.append(np.min(weighted_data[:, i]))
            else:
                ideal_best.append(np.min(weighted_data[:, i]))
                ideal_worst.append(np.max(weighted_data[:, i]))

        s_plus = np.sqrt(((weighted_data - ideal_best) ** 2).sum(axis=1))
        s_minus = np.sqrt(((weighted_data - ideal_worst) ** 2).sum(axis=1))
        score = s_minus / (s_plus + s_minus)

        df['Topsis Score'] = score
        df['Rank'] = df['Topsis Score'].rank(ascending=False).astype(int)
        
        output_path = os.path.join(app.config['UPLOAD_FOLDER'], 'result.csv')
        df.to_csv(output_path, index=False)
        return output_path, None

    except Exception as e:
        return None, str(e)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 1. Check File
        if 'datafile' not in request.files:
            flash('No file part', 'error')
            return render_template('form.html')
        file = request.files['datafile']
        if file.filename == '':
            flash('No selected file', 'error')
            return render_template('form.html')

        # 2. Get Form Data
        email = request.form['email']
        weights_str = request.form['weights']
        impacts_str = request.form['impacts']

        # 3. Validate Email
        if not validate_email(email):
            flash('Invalid Email format', 'error')
            return render_template('form.html')

        # 4. Validate and Parse Weights/Impacts
        try:
            weights = [float(w) for w in weights_str.split(',')]
            impacts = impacts_str.split(',')
            if not all(i in ['+', '-'] for i in impacts):
                raise ValueError("Impacts must be + or -")
        except:
            flash('Invalid format for Weights or Impacts', 'error')
            return render_template('form.html')

        # 5. Save File & Run Topsis
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        result_path, error_msg = run_topsis(file_path, weights, impacts)
        
        if error_msg:
            flash(f"Error: {error_msg}", 'error')
        else:
            # 6. Send Email
            if send_email(email, result_path):
                flash(f'Success! Result sent to {email}', 'success')
            else:
                flash('Processing done, but failed to send email. Check console/logs.', 'error')

    return render_template('form.html')

if __name__ == '__main__':

    app.run(debug=True)
