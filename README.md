# Smart Classroom Attendance System  


An IoT-based automated attendance system using facial recognition, built for Raspberry Pi with Flask web interface.

## ✨ Key Features  
- **94.2% accurate** face recognition using dlib's ResNet  
- Real-time processing at **4.7 FPS** on Raspberry Pi 4  
- Multi-face detection (**91.6%** accuracy for 2 faces)  
- Automated Excel/PDF reporting with email alerts  
- Secure web dashboard with role-based access  

## 🛠️ Technology Stack  
| Component       | Technology Used          |
|----------------|--------------------------|
| Face Recognition | `face_recognition` (dlib) |
| Backend        | Python Flask             |
| Database       | SQLite                   |
| Hardware       | Raspberry Pi + Camera Module|
| Frontend       | Bootstrap 5 + Chart.js   |

## 📦 Installation  

### Prerequisites  
- Raspberry Pi OS (64-bit)  
- Python 3.9+  
 

```bash
# Clone the repository  
git clone https://github.com/yourusername/smart-attendance.git  
cd smart-attendance  
 
# Initialize database  
python s1.py  

# Start the system  
python a1fr.py  
