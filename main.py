import sys
import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
import firebase_admin
from firebase_admin import credentials

# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Импортируем загрузчик моделей ---
# Убедитесь, что model_loader.py находится в той же директории, что и main.py
# (то есть в корне проекта, или /app в контейнере)
try:
    from model_loader import load_models
except ImportError as e:
    print(f"CRITICAL ERROR: Failed to import model_loader. Check file existence and path. Error: {e}")
    # Можно добавить sys.exit(1) здесь для более явного падения
    raise
# -----------------------------------------------------------

# --- РЕШЕНИЕ ПРОБЛЕМЫ С ИМПОРТАМИ (оставляем, не помешает) ---
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
# -----------------------------------------------------------

# --- Инициализация Firebase Admin SDK из секрета RunPod ---
# ... (ваш код инициализации Firebase без изменений) ...
if 'FIREBASE_CREDS_JSON' in os.environ:
    try:
        creds_json_str = os.environ['FIREBASE_CREDS_JSON']
        creds_dict = json.loads(creds_json_str)
        cred = credentials.Certificate(creds_dict)
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized successfully!")
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase Admin SDK: {e}")
else:
    print("WARNING: FIREBASE_CREDS_JSON secret not found. Firebase features will be disabled.")


app = FastAPI(
    title="AI Makeup Backend",
    description="Backend API for AI makeup generation",
    version="1.0.0"
)

# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Загрузка моделей при старте приложения ---
@app.on_event("startup")
async def startup_event():
    print("Запуск FastAPI: Инициализация моделей AI...")
    try:
        app.state.MODELS = load_models() # Загружаем модели и сохраняем их в состоянии приложения
        print("FastAPI startup complete: AI models loaded.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load AI models during startup. Error: {e}")
        # Это приведет к падению Uvicorn, что мы и хотим для явной ошибки
        raise 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "AI Makeup Backend API is running!"}