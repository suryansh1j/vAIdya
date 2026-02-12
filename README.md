# vAIdya - AI-Powered Medical Assistant 🏥

**MediCare-Inspired Medical Audio Transcription & Patient Management System**

> Transform patient audio consultations into structured medical notes with AI-powered transcription, symptom extraction, and comprehensive patient records management.

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 🌟 Features

### 🎤 Audio Processing
- **Browser Recording** - Record consultations directly using MediaRecorder API
- **File Upload** - Drag-and-drop support for .m4a, .wav, .mp3, .ogg
- **AI Transcription** - Faster-Whisper for accurate speech-to-text
- **Real-time Progress** - Visual feedback with loading states

### 🤖 AI-Powered Extraction
- **Symptom Detection** - Automatic extraction with negation handling (affirmed/negated)
- **Patient Information** - 10 structured fields extracted:
  - Name, Age, Gender
  - Chief Complaint
  - Past Medical History
  - Family History
  - Previous Surgeries
  - Lifestyle
  - Allergies
  - Current Medications

### 💼 Patient Management
- **Searchable Records** - Find patients quickly
- **Detailed Views** - Complete patient history
- **PDF Export** - Download formatted notes
- **Multi-user Support** - JWT authentication

### 🎨 Modern Interface
- **MediCare Design** - Professional medical aesthetic
- **4-Tab Navigation** - Audio Processing, Chat Assistant, Patient Records, Health Checker
- **Responsive** - Works on desktop, tablet, and mobile
- **Dark Mode Ready** - Clean, modern UI

---

## � Quick Start

### Prerequisites
- Python 3.12+
- ffmpeg
- 4GB+ RAM

### Local Development

```bash
# Clone repository
git clone https://github.com/yourusername/vAIdya.git
cd vAIdya

# Install dependencies
pip install -r requirements.txt

# Set up environment
copy .env.example .env

# Run server
python run.py
```

Visit http://localhost:8000

### Deploy to Render (Free!)

1. **Push to GitHub**
```bash
git remote add origin https://github.com/YOUR_USERNAME/vAIdya.git
git push -u origin main
```

2. **Create PostgreSQL Database**
- Go to https://render.com
- New + → PostgreSQL → Free plan
- Copy Internal Database URL

3. **Create Web Service**
- New + → Web Service
- Connect GitHub repo
- Runtime: Python 3
- Build: `pip install -r requirements.txt`
- Start: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

4. **Add Environment Variables**
```
DATABASE_URL=<your-postgres-url>
SECRET_KEY=<generate-with-secrets.token_urlsafe(32)>
ENVIRONMENT=production
DEBUG=False
ALLOWED_ORIGINS=https://your-app.onrender.com
```

5. **Deploy!** 🎉

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **PyTorch** - Deep learning (CPU mode)
- **Transformers** - Hugging Face NLP models
- **spaCy** - Industrial-strength NLP
- **Faster-Whisper** - Audio transcription
- **SQLAlchemy** - Database ORM
- **JWT** - Secure authentication

### Frontend
- **Vanilla JavaScript** - No framework overhead
- **HTML5/CSS3** - Modern web standards
- **MediaRecorder API** - Browser audio recording
- **Responsive Design** - Mobile-first approach

### AI Models
- **DistilBERT** - Question answering
- **NegSpacy** - Medical negation detection
- **Faster-Whisper** - Speech recognition

### Database
- **SQLite** - Local development
- **PostgreSQL** - Production (Render, Supabase, etc.)

---

## 📁 Project Structure

```
vAIdya/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── models.py            # Database models
│   ├── auth.py              # JWT authentication
│   ├── nlp_processor.py     # AI pipeline
│   ├── config.py            # Configuration
│   ├── database.py          # Database setup
│   └── logger.py            # Logging
├── frontend/
│   ├── index.html           # Main app (4 tabs)
│   ├── doctor_notes.html    # Notes editor
│   ├── scripts/
│   │   ├── auth.js          # Authentication
│   │   ├── index.js         # Main logic
│   │   └── doctor_notes.js  # Notes logic
│   └── style/
│       ├── index.css        # Main styles
│       └── doctor_notes.css # Notes styles
├── audio/                   # Uploaded audio files
├── transcripts/             # Generated transcripts
├── .env                     # Environment variables
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker configuration
├── render.yaml             # Render deployment
└── README.md               # This file
```

---

## 🎯 Usage

### 1. Register/Login
- Create account with username, email, password
- JWT token stored in localStorage

### 2. Record or Upload Audio
- **Record:** Click microphone → speak → stop
- **Upload:** Drag file or browse

### 3. Process Audio
- Click "Process Audio"
- Wait 1-5 minutes (first run downloads models)
- View results:
  - Full transcript
  - Patient information
  - Symptoms (affirmed/negated)

### 4. Manage Records
- View all patients in "Patient Records" tab
- Search by name, date, symptoms
- Click patient to view details
- Download PDF notes

---

## 🔧 Configuration

### Environment Variables

```bash
# Application
APP_NAME=vAIdya
DEBUG=True
ENVIRONMENT=development

# Server
HOST=0.0.0.0
PORT=8000

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
DATABASE_URL=sqlite:///./vaidya.db
# For PostgreSQL: postgresql://user:password@host/db

# CORS
ALLOWED_ORIGINS=http://localhost:8000

# ML Models
WHISPER_MODEL=Systran/faster-distil-whisper-large-v2
WHISPER_DEVICE=cpu
```

---

## 🚢 Deployment Options

### Render (Recommended - Free)
- Free PostgreSQL database
- Free web hosting
- Auto-deploy from GitHub
- See deployment guide above

### Fly.io
- Modern CLI-based deployment
- Free tier: 3 apps
- Global edge network
```bash
fly launch
fly deploy
```

### Docker
```bash
docker-compose up -d
```

---

## 🧪 API Endpoints

### Authentication
```
POST /api/v1/auth/register - Register new user
POST /api/v1/auth/login    - Login user
GET  /api/v1/auth/me       - Get current user
```

### Audio Processing
```
POST /api/v1/upload-audio  - Upload and process audio
```

### Patient Management
```
GET  /api/v1/patients      - List all patients
GET  /api/v1/patients/{id} - Get patient details
```

### Health
```
GET  /api/v1/health        - Health check
```

---

## 🎨 Design System

### Colors
- **Primary Blue:** #2563EB
- **Purple:** #A855F7
- **Pink:** #EC4899
- **Green:** #10B981
- **Background:** #F5F7FA

### Components
- Gradient hero banners
- Card-based layouts
- Smooth animations
- Loading states
- Toast notifications

---

## 🐛 Troubleshooting

### FFmpeg Not Found
```bash
# Windows (Chocolatey)
choco install ffmpeg

# Or download from: https://www.gyan.dev/ffmpeg/builds/
```

### Build Fails on Render
- Check logs for missing dependencies
- Ensure all packages in requirements.txt
- Verify Python version compatibility

### Registration Fails
- Check DATABASE_URL is set
- Verify SECRET_KEY is generated
- Check server logs for errors

### Slow First Load
- ML models download on first run (~500MB)
- Subsequent loads are faster
- Consider pre-downloading models

---

## 📊 Performance

- **First audio processing:** 3-5 minutes (model download)
- **Subsequent processing:** 30-60 seconds
- **Database:** SQLite (local) or PostgreSQL (production)
- **Memory usage:** ~2GB with models loaded

---

## 🗺️ Roadmap

### Completed ✅
- [x] Audio transcription
- [x] Symptom extraction
- [x] Patient info extraction
- [x] User authentication
- [x] Patient records
- [x] PDF export
- [x] Modern UI
- [x] Deployment ready

### Planned 🚧
- [ ] Chat assistant (AI doctor)
- [ ] Health symptom checker
- [ ] Prescription scanning (OCR)
- [ ] Medication database
- [ ] Appointment booking
- [ ] Multi-language support
- [ ] Voice response (TTS)
- [ ] Mobile app

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Open pull request

---

## 📄 License

MIT License - see LICENSE file for details

---

## 👨‍� Author

**Your Name**
- GitHub: [@yourusername](https://github.com/yourusername)
- Email: your.email@example.com

---

## 🙏 Acknowledgments

- **Cyfuture AI Hackathon 1.0** - For the opportunity
- **Hugging Face** - For transformer models
- **OpenAI** - For Whisper architecture
- **FastAPI** - For excellent documentation
- **spaCy** - For NLP tools

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/yourusername/vAIdya/issues)
- **Discussions:** [GitHub Discussions](https://github.com/yourusername/vAIdya/discussions)
- **Email:** support@vaidya.com

---

**Built with ❤️ for better healthcare**