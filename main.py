import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import router
import firebase_admin
from firebase_admin import credentials

# --- Инициализация Firebase Admin SDK из секрета RunPod ---
# Проверяем, есть ли наш секрет в переменных окружения
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