import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    BASE_DIR = BASE_DIR
    SECRET_KEY = os.environ.get('SECRET_KEY', 'college-grievance-secret-key-2026-secure')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1')
    WTF_CSRF_ENABLED = True
    
    # Database
    IS_VERCEL = os.environ.get('VERCEL') == '1' or os.environ.get('VERCEL_ENV') is not None
    
    if IS_VERCEL:
        DB_DIR = '/tmp'
        DB_PATH = os.path.join(DB_DIR, 'grievance.db')
        seed_db = os.path.join(BASE_DIR, 'database', 'grievance.db')
        if not os.path.exists(DB_PATH) and os.path.exists(seed_db):
            try:
                import shutil
                shutil.copyfile(seed_db, DB_PATH)
            except Exception:
                pass
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
        UPLOAD_FOLDER = os.path.join('/tmp', 'uploads')
        try:
            os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        except Exception:
            pass
    else:
        DB_DIR = os.path.join(BASE_DIR, 'database')
        os.makedirs(DB_DIR, exist_ok=True)
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{os.path.join(DB_DIR, 'grievance.db')}"
        UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Upload limits
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max file upload
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    # ML Models directory
    MODELS_DIR = os.path.join(BASE_DIR, 'models')
    os.makedirs(MODELS_DIR, exist_ok=True)
    CATEGORY_MODEL_PATH = os.path.join(MODELS_DIR, 'category_model.pkl')
    PRIORITY_MODEL_PATH = os.path.join(MODELS_DIR, 'priority_model.pkl')
    SENTIMENT_MODEL_PATH = os.path.join(MODELS_DIR, 'sentiment_model.pkl')
    VECTORIZER_PATH = os.path.join(MODELS_DIR, 'tfidf_vectorizer.pkl')
    
    # Duplicate Detection
    SIMILARITY_THRESHOLD = 0.55  # Cosine similarity threshold for duplicate alert
    
    # Category to Department Mapping
    CATEGORY_DEPARTMENT_MAPPING = {
        'Academic': 'Academic Office',
        'Examination': 'Examination Cell',
        'Hostel': 'Hostel Administration',
        'Transport': 'Transport Office',
        'Infrastructure': 'Maintenance Department',
        'Library': 'Library Administration',
        'Administration': 'Administrative Office',
        'Other': 'Administrative Office'
    }
    
    # Physical Danger / Emergency Safety Keywords for Rule-Based Escalation
    CRITICAL_SAFETY_KEYWORDS = [
        'fire', 'spark', 'sparks', 'shock', 'electric', 'short circuit',
        'exposed wire', 'wiring', 'gas leak', 'chemical leak', 'collapse',
        'structural crack', 'flood', 'violence', 'assault', 'hazard',
        'smoke', 'explosion', 'emergency', 'danger', 'bleeding', 'injury'
    ]
