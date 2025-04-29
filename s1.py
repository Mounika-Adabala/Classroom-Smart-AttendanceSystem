import sqlite3
import os
from werkzeug.security import generate_password_hash

def init_db():
    os.makedirs('D:/AS/database', exist_ok=True)
    os.makedirs('D:/AS/known_faces', exist_ok=True)
    os.makedirs('D:/AS/reports', exist_ok=True)
    os.makedirs('D:/AS/debug', exist_ok=True)
    
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
    
    # Add admin user
    try:
        hashed_password = generate_password_hash('admin123')
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                     ('admin', hashed_password))
    except sqlite3.IntegrityError:
        pass
    
    # Add sample students (make sure these images exist)
    sample_students = [
        ('501', 'mounika', 'D:/AS/known_faces/Srujana.jpg'),
        ('511', 'srujana', 'D:/AS/known_faces/Mounika.jpg'),
        ('545', 'harshi', 'D:/AS/known_faces/Harshitha.jpg'),
        ('569', 'suchi', 'D:/AS/known_faces/569.jpg'),
        ('500', 'Bujji', 'D:/AS/known_faces/Bujji.jpg')
    ]
    
    for student in sample_students:
        try:
            cursor.execute('INSERT INTO students (student_id, name, image_path) VALUES (?, ?, ?)', student)
        except sqlite3.IntegrityError:
            pass

    # Add metrics table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            detection_time REAL,
            recognition_time REAL,
            fps REAL
    )''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()