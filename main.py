# --- РЕШЕНИЕ ПРОБЛЕМЫ С ИМПОРТАМИ ---
# Убедимся, что Python знает, где искать модули в нашем приложении.
# Это добавляет текущую директорию (/app в контейнере) в путь поиска модулей.
import sys
import os
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
print(f"Added {current_dir} to sys.path. Current sys.path: {sys.path}") # <-- Для отладки
# -----------------------------------------

import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
import firebase_admin
from firebase_admin import credentials
from model_loader import load_models

# --- КЛЮЧЕВОЕ ИЗМЕНЕНИЕ: Теперь импортируем model_loader как обычный модуль ---
# Он должен быть в корневом каталоге проекта (рядом с main.py)
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
        # Не выходим, чтобы увидеть другие ошибки, но для продакшна лучше sys.exit(1)
else:
    print("WARNING: FIREBASE_CREDS_JSON secret not found. Firebase features will be disabled.")


app = FastAPI(
    title="AI Makeup Backend",
    description="Backend API for AI makeup generation",
    version="1.0.0"
)

# --- Загрузка моделей при старте приложения ---
@app.on_event("startup")
async def startup_event():
    print("FastAPI Startup Event: Initializing AI models (from pre-downloaded cache)...")
    try:
        app.state.MODELS = load_models() # Модели теперь будут загружаться быстро из кэша
        print("FastAPI Startup Event: AI models loaded successfully.")
    except Exception as e:
        print(f"CRITICAL ERROR: Failed to load AI models during startup. Error: {e}")
        raise # FastAPI упадет, если модели не загрузятся

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