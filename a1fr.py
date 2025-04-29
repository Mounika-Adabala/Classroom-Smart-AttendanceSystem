from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import os
from datetime import datetime
import threading
import csv
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this to a secure random key in production

# Email configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '1296group@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'vnkslgfcdrqpuipe'  # Replace with your password
app.config['MAIL_DEFAULT_SENDER'] = '1296group@gmail.com'  # Replace with your email
app.config['FACULTY_EMAIL'] = 'mouny1234567@gmail.com'  # Replace with faculty email

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, user_id):
        self.id = user_id

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('D:/AS/database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    conn.close()
    return User(user_data[0]) if user_data else None

# Database Initialization
def init_db():
    conn = sqlite3.connect('D:/AS/database/attendance.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT NOT NULL,
        name TEXT NOT NULL,
        date TEXT NOT NULL,
        time TEXT NOT NULL,
        status TEXT NOT NULL,
        confidence REAL,
        subject TEXT DEFAULT 'General',
        debug_image TEXT
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        image_path TEXT NOT NULL
    )''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )''')
    
    # Add admin user if not exists
    try:
        hashed_password = generate_password_hash('admin123')
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                     ('admin', hashed_password))
    except sqlite3.IntegrityError:
        pass
    
    conn.commit()
    conn.close()

# Initialize database at startup
os.makedirs('D:/AS/database', exist_ok=True)
os.makedirs('D:/AS/known_faces', exist_ok=True)
os.makedirs('D:/AS/reports', exist_ok=True)
os.makedirs('D:/AS/debug', exist_ok=True)
os.makedirs('D:/AS/static/uploads', exist_ok=True)

if not os.path.exists('D:/AS/database/attendance.db'):
    init_db()

# Email sending function
def send_email_with_attachment(subject, body, to_email, attachment_path):
    try:
        msg = MIMEMultipart()
        msg['From'] = app.config['MAIL_DEFAULT_SENDER']
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        with open(attachment_path, 'rb') as attachment:
            part = MIMEApplication(attachment.read(), Name=os.path.basename(attachment_path))
            part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
            msg.attach(part)
        
        with smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT']) as server:
            server.starttls()
            server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            server.send_message(msg)
        
        return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

# Application Routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = sqlite3.connect('D:/AS/database/attendance.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, password FROM users WHERE username = ?', (username,))
        user_data = cursor.fetchone()
        conn.close()
        
        if user_data and check_password_hash(user_data[1], password):
            user = User(user_data[0])
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = sqlite3.connect('D:/AS/database/attendance.db')
    cursor = conn.cursor()
    
    # Get recent attendance records
    cursor.execute('''
        SELECT a.student_id, s.name, a.date, a.time, a.status, a.subject, a.confidence
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        ORDER BY a.date DESC, a.time DESC
        LIMIT 10
    ''')
    recent_records = cursor.fetchall()
    
    # Get attendance summary
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Recognized' THEN 1 ELSE 0 END) as recognized,
            SUM(CASE WHEN status = 'Not Recognized' THEN 1 ELSE 0 END) as not_recognized
        FROM attendance
        WHERE date = ?
    ''', (datetime.now().strftime("%Y-%m-%d"),))
    stats = cursor.fetchone()
    
    # Get monthly summary
    cursor.execute('''
        SELECT 
            strftime('%Y-%m', date) as month,
            COUNT(*) as total,
            SUM(CASE WHEN status = 'Recognized' THEN 1 ELSE 0 END) as recognized
        FROM attendance
        GROUP BY strftime('%Y-%m', date)
        ORDER BY month DESC
        LIMIT 6
    ''')
    monthly_stats = cursor.fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         recent_records=recent_records,
                         stats=stats,
                         monthly_stats=monthly_stats)

@app.route('/take_attendance', methods=['GET', 'POST'])
@login_required
def take_attendance():
    if request.method == 'POST':
        subject = request.form.get('subject', 'General')
        
        try:
            from facefr import FaceRecognizer
            recognizer = FaceRecognizer(device_type='pi')
            
            # Run recognition
            results = recognizer.run_recognition(subject)
            
            # Process results
            if results and results[0]['status'] not in ['Error', 'No Faces Detected']:
                flash(f'Attendance recorded for {subject}! Recognized {len([r for r in results if r["status"] == "Recognized"])} students.', 'success')
            else:
                flash('Attendance recording completed, but no students were recognized.', 'warning')
                
            return redirect(url_for('dashboard'))
            
        except Exception as e:
            flash(f'Error during attendance recording: {str(e)}', 'danger')
            return redirect(url_for('take_attendance'))
    
    return render_template('take_attendance.html')

@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        name = request.form.get('name')
        photo = request.files.get('photo')
        
        if not student_id or not name or not photo:
            flash('All fields are required', 'danger')
            return redirect(url_for('add_student'))
        
        # Save the photo
        filename = f"{student_id}_{name}.jpg"
        photo_path = os.path.join('D:/AS/known_faces', filename)
        photo.save(photo_path)
        
        # Save to database
        conn = sqlite3.connect('D:/AS/database/attendance.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO students (student_id, name, image_path) VALUES (?, ?, ?)',
                         (student_id, name, photo_path))
            conn.commit()
            flash('Student added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Student ID already exists', 'danger')
        finally:
            conn.close()
        
        return redirect(url_for('dashboard'))
    
    return render_template('add_student.html')

@app.route('/get_recent_attendance')
@login_required
def get_recent_attendance():
    conn = sqlite3.connect('D:/AS/database/attendance.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT a.student_id, s.name, a.date, a.time, a.status, a.subject, a.confidence
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        ORDER BY a.date DESC, a.time DESC
        LIMIT 10
    ''')
    records = cursor.fetchall()
    conn.close()
    return jsonify([dict(zip(['student_id', 'name', 'date', 'time', 'status', 'subject', 'confidence'], row)) for row in records])

@app.route('/reports')
@login_required
def reports():
    reports_dir = 'D:/AS/reports'
    os.makedirs(reports_dir, exist_ok=True)
    
    report_files = []
    for filename in os.listdir(reports_dir):
        if filename.endswith('.csv'):
            filepath = os.path.join(reports_dir, filename)
            report_files.append({
                'name': filename,
                'size': os.path.getsize(filepath),
                'modified': datetime.fromtimestamp(os.path.getmtime(filepath))
            })
    
    report_files.sort(key=lambda x: x['modified'], reverse=True)
    return render_template('reports.html', report_files=report_files)

@app.route('/generate_report', methods=['POST'])
@login_required
def generate_report():
    month = request.form.get('month')
    subject = request.form.get('subject', 'All')
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"attendance_report_{subject}_{month}_{timestamp}.csv"
    filepath = os.path.join('D:/AS/reports', filename)
    
    conn = sqlite3.connect('D:/AS/database/attendance.db')
    cursor = conn.cursor()
    
    query = '''
        SELECT a.date, a.time, a.student_id, s.name, a.status, a.confidence, a.subject
        FROM attendance a
        LEFT JOIN students s ON a.student_id = s.student_id
        WHERE strftime('%Y-%m', a.date) = ?
    '''
    params = [month]
    
    if subject != 'All':
        query += " AND a.subject = ?"
        params.append(subject)
        
    query += " ORDER BY a.date DESC, a.time DESC"
    
    cursor.execute(query, params)
    data = cursor.fetchall()
    conn.close()
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date', 'Time', 'Student ID', 'Name', 'Status', 'Confidence', 'Subject'])
        writer.writerows(data)
    
    # Send email with the report
    email_subject = f"Attendance Report - {subject} - {month}"
    email_body = f"Please find attached the attendance report for {subject} for {month}."
    
    if send_email_with_attachment(
        email_subject,
        email_body,
        app.config['FACULTY_EMAIL'],
        filepath
    ):
        flash(f'Report generated and emailed successfully: {filename}', 'success')
    else:
        flash(f'Report generated but email failed: {filename}', 'warning')
    
    return redirect(url_for('reports'))

@app.route('/download_report/<filename>')
@login_required
def download_report(filename):
    return send_from_directory(
        'D:/AS/reports',
        filename,
        as_attachment=True,
        mimetype='text/csv'
    )

@app.route('/delete_report/<filename>')
@login_required
def delete_report(filename):
    try:
        filepath = os.path.join('D:/AS/reports', filename)
        if os.path.exists(filepath):
            os.remove(filepath)
            flash(f'Report deleted: {filename}', 'success')
        else:
            flash('Report not found', 'warning')
    except Exception as e:
        flash(f'Error deleting report: {str(e)}', 'danger')
    return redirect(url_for('reports'))

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/metrics')
@login_required
def show_metrics():
    from metrics import calculate_accuracy_metrics, get_hardware_metrics
    
    accuracy_metrics = calculate_accuracy_metrics()
    hardware_metrics = get_hardware_metrics()
    
    return render_template('metrics.html', 
                         accuracy_metrics=accuracy_metrics,
                         hardware_metrics=hardware_metrics)

@app.route('/api/metrics')
@login_required
def get_metrics():
    from metrics import calculate_accuracy_metrics, get_hardware_metrics
    return jsonify({
        'accuracy': calculate_accuracy_metrics(),
        'hardware': get_hardware_metrics()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)