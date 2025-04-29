import cv2
import os
import sqlite3
import time
from datetime import datetime
import logging
import shutil
import face_recognition
import numpy as np
import time

# Configure application logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FaceRecognizer:
    def __init__(self, device_type='pi'):
        self.device_type = device_type
        self.known_faces_dir = "D:/AS/known_faces"
        self.temp_image_path = "D:/AS/temp_capture.jpg"
        self.camera = None
        self.known_face_encodings = []
        self.known_face_ids = []
        self.known_face_names = []
        self.load_known_faces()
        self.initialize_camera()
        
    def load_known_faces(self):
        conn = sqlite3.connect('D:/AS/database/attendance.db')
        cursor = conn.cursor()
        cursor.execute('SELECT student_id, name, image_path FROM students')
        known_students = cursor.fetchall()
        conn.close()

        for student_id, name, image_path in known_students:
            try:
                image = face_recognition.load_image_file(image_path)
                encodings = face_recognition.face_encodings(image)
                if len(encodings) > 0:
                    self.known_face_encodings.append(encodings[0])
                    self.known_face_ids.append(student_id)
                    self.known_face_names.append(name)
            except Exception as e:
                logger.warning(f"Failed to load face for {name}: {str(e)}")
                continue

    def initialize_camera(self):
        try:
            # Camera settings
            self.camera = cv2.VideoCapture(0)
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            time.sleep(2)  # Camera warm-up
                
            if not self.camera.isOpened():
                raise RuntimeError("Could not initialize camera")
                
        except Exception as e:
            logger.error(f"Camera initialization failed: {str(e)}")
            raise

    def capture_image(self):
        try:
            ret, frame = self.camera.read()
            if not ret:
                raise RuntimeError("Failed to capture image from camera")
            return frame
        except Exception as e:
            logger.error(f"Image capture failed: {str(e)}")
            raise

    def recognize_faces(self, image):
        results = []
        debug_path = None
        start_time = time.time()  # Start timing for entire process
    
        try:
            # Save temporary image
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            cv2.imwrite(self.temp_image_path, image)
            
            # Store the captured image for debugging
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_path = f"debug/capture_{timestamp}.jpg"
            os.makedirs("debug", exist_ok=True)
            shutil.copy(self.temp_image_path, debug_path)
            
            # Find faces in the captured image - start face detection timing
            face_detection_start = time.time()
            face_locations = face_recognition.face_locations(rgb_image)
            detection_time = time.time() - face_detection_start
            
            # Face encoding and matching - start recognition timing
            recognition_start = time.time()
            face_encodings = face_recognition.face_encodings(rgb_image, face_locations)

            for face_encoding in face_encodings:
                # Compare with known faces
                matches = face_recognition.compare_faces(self.known_face_encodings, face_encoding, tolerance=0.5)
                face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
                
                best_match_index = np.argmin(face_distances) if len(face_distances) > 0 else None
                
                if best_match_index is not None and matches[best_match_index]:
                    confidence = 1 - face_distances[best_match_index]
                    results.append({
                        'student_id': self.known_face_ids[best_match_index],
                        'name': self.known_face_names[best_match_index],
                        'confidence': confidence,
                        'status': 'Recognized',
                        'debug_image': debug_path,
                        'metrics': {
                            'detection_time': round(detection_time * 1000, 2),  # in milliseconds
                            'recognition_time': round((time.time() - recognition_start) * 1000, 2)
                        }
                    })
            
            if not results and len(face_locations) > 0:
                results.append({
                    'student_id': 'unknown',
                    'name': 'Unknown',
                    'confidence': 0,
                    'status': 'Not Recognized',
                    'debug_image': debug_path,
                    'metrics': {
                        'detection_time': round(detection_time * 1000, 2),
                        'recognition_time': round((time.time() - recognition_start) * 1000, 2)
                    }
                })
            elif not results:
                results.append({
                    'student_id': 'none',
                    'name': 'No Faces',
                    'confidence': 0,
                    'status': 'No Faces Detected',
                    'debug_image': debug_path,
                    'metrics': {
                        'detection_time': round(detection_time * 1000, 2),
                        'recognition_time': 0  # No recognition attempted
                    }
                })
                
            return results
            
        except Exception as e:
            logger.error(f"Recognition failed: {str(e)}")
            return [{
                'student_id': 'error',
                'name': 'Error',
                'confidence': 0,
                'status': f'Error: {str(e)}',
                'debug_image': debug_path if debug_path else None,
                'metrics': {
                    'detection_time': 0,
                    'recognition_time': 0
                }
            }]
            
        finally:
            if os.path.exists(self.temp_image_path):
                os.remove(self.temp_image_path)

    def save_to_database(self, recognition_results, subject='General'):
        conn = None
        try:
            conn = sqlite3.connect('D:/AS/database/attendance.db')
            cursor = conn.cursor()
            
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")
            time_str = now.strftime("%H:%M:%S")
            
            for result in recognition_results:
                cursor.execute('''
                    INSERT INTO attendance (student_id, name, date, time, status, confidence, subject, debug_image)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result['student_id'],
                    result['name'],
                    date_str,
                    time_str,
                    result['status'],
                    result.get('confidence', 0),
                    subject,
                    result.get('debug_image', None)
                ))
            
            conn.commit()
            logger.info(f"Saved {len(recognition_results)} records to database")
            
        except Exception as e:
            logger.error(f"Database save failed: {str(e)}")
            raise
            
        finally:
            if conn:
                conn.close()

    def run_recognition(self, subject='General'):
        try:
            logger.info("Starting face recognition process...")
            
            # Capture image
            frame = self.capture_image()
            
            # Recognize faces
            results = self.recognize_faces(frame)
            
            # Save results
            self.save_to_database(results, subject)
            
            return results
            
        except Exception as e:
            logger.error(f"Recognition process failed: {str(e)}")
            return [{
                'student_id': 'error',
                'name': 'Error',
                'confidence': 0,
                'status': f'Error: {str(e)}',
                'debug_image': None
            }]

    def cleanup(self):
        if hasattr(self, 'camera') and self.camera and self.camera.isOpened():
            self.camera.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    recognizer = None
    try:
        recognizer = FaceRecognizer(device_type='pi')
        print("Capturing image...")
        image = recognizer.capture_image()
        print("Recognizing faces...")
        results = recognizer.recognize_faces(image)
        print("Saving to database...")
        recognizer.save_to_database(results)
        print("\nRecognition Results:")
        for result in results:
            print(f"{result['name']}: {result['status']} (Confidence: {result.get('confidence', 0):.2f}")
            if result.get('debug_image'):
                print(f"Debug image: {result['debug_image']}")
            
    except Exception as e:
        print(f"Fatal error: {str(e)}")
    finally:
        if recognizer:
            recognizer.cleanup()