import cv2
import face_recognition
import os
import numpy as np

KNOWN_FACES_DIR = "D:/AS/known_faces"
TOLERANCE = 0.5
FRAME_THICKNESS = 3
FONT_THICKNESS = 2
MODEL = "hog"  # 'cnn' is more accurate but slower

print("🔄 Loading known faces...")

known_faces = []
known_names = []

# Load known faces
for name in os.listdir(KNOWN_FACES_DIR):
    person_dir = os.path.join(KNOWN_FACES_DIR, name)
    if not os.path.isdir(person_dir):
        continue

    for filename in os.listdir(person_dir):
        image_path = os.path.join(person_dir, filename)
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)

        if len(encodings) > 0:
            known_faces.append(encodings[0])
            known_names.append(name)
        else:
            print(f"⚠️ No face found in {filename}, skipping.")

print("✅ Known faces loaded. Starting camera...")

# Start video capture
video = cv2.VideoCapture(0)

if not video.isOpened():
    raise RuntimeError("❌ Could not open camera.")

while True:
    ret, image = video.read()
    if not ret:
        print("❌ Failed to grab frame.")
        break

    # Resize frame for faster processing
    small_frame = cv2.resize(image, (0, 0), fx=0.25, fy=0.25)
    rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_small_frame, model=MODEL)
    face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

    for face_encoding, face_location in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces(known_faces, face_encoding, TOLERANCE)
        face_distances = face_recognition.face_distance(known_faces, face_encoding)

        name = "Unknown"

        if matches:
            best_match_index = np.argmin(face_distances)
            if matches[best_match_index]:
                name = known_names[best_match_index]

        # Scale face locations back to original size
        top, right, bottom, left = [v * 4 for v in face_location]

        cv2.rectangle(image, (left, top), (right, bottom), (0, 255, 0), FRAME_THICKNESS)
        cv2.putText(image, name, (left + 6, bottom + 25), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), FONT_THICKNESS)

    cv2.imshow("Face Recognition", image)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

video.release()
cv2.destroyAllWindows()
