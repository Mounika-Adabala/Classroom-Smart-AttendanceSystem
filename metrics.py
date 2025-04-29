import sqlite3
import numpy as np
from datetime import datetime, timedelta

def calculate_accuracy_metrics():
    """Calculate TAR, FAR, FRR from the database"""
    conn = sqlite3.connect('D:/AS/database/attendance.db')
    cursor = conn.cursor()
    
    # Get all recognition attempts from last 7 days
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    cursor.execute('''
        SELECT status, COUNT(*) as count 
        FROM attendance 
        WHERE date BETWEEN ? AND ?
        GROUP BY status
    ''', (start_date, end_date))
    
    status_counts = dict(cursor.fetchall())
    
    # Calculate metrics
    true_positives = status_counts.get('Recognized', 0)
    false_positives = status_counts.get('Not Recognized', 0)
    false_negatives = status_counts.get('No Faces Detected', 0)  # Assuming these are actual students
    
    total_attempts = sum(status_counts.values())
    
    # Metrics calculation
    tar = true_positives / (true_positives + false_negatives) * 100 if (true_positives + false_negatives) > 0 else 0
    far = false_positives / (false_positives + (total_attempts - true_positives - false_positives)) * 100 if (false_positives + (total_attempts - true_positives - false_positives)) > 0 else 0
    frr = false_negatives / (true_positives + false_negatives) * 100 if (true_positives + false_negatives) > 0 else 0
    overall_accuracy = true_positives / total_attempts * 100 if total_attempts > 0 else 0
    
    conn.close()
    
    return {
        'TAR': round(tar, 2),
        'FAR': round(far, 2),
        'FRR': round(frr, 2),
        'Overall Accuracy': round(overall_accuracy, 2),
        'Total Attempts': total_attempts
    }

def get_hardware_metrics():
    """Simulate hardware metrics (you should replace with actual measurements)"""
    return {
        'FPS': 4.7,
        'Face Detection Latency (ms)': 210,
        'Recognition Latency (ms)': 320,
        'Power Consumption (W)': 2.8
    }