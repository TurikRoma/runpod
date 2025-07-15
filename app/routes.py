# routes.py

import torch
import numpy as np
import base64
import io
import requests
import google.generativeai as genai

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import HttpUrl
from PIL import Image

# Локальные импорты обновленных моделей
from .models import GenerateMakeupRequest, GenerateMakeupResponse

# --- КОНФИГУРАЦИЯ API (предполагается, что она загружается из окружения) ---
# УБЕДИТЕСЬ, ЧТО API_KEY ЗАГРУЖАЕТСЯ БЕЗОПАСНО, А НЕ ЖЕСТКО ЗАКОДИРОВАН
# Например: API_KEY = os.getenv("GEMINI_API_KEY")
API_KEY = "YOUR_GEMINI_API_KEY" # Замените на ваш ключ или метод загрузки
genai.configure(api_key=API_KEY)

router = APIRouter()

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (перенесены из main.py) ---

def download_image(url: HttpUrl) -> Image.Image:
    """Скачивает изображение по URL и возвращает объект PIL Image."""
    try:
        response = requests.get(str(url), stream=True, timeout=15)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        return image
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Не удалось скачать изображение по URL: {url}. Ошибка: {e}")

async def get_prompt_from_llm(reference_image: Image.Image) -> str:
    """Отправляет референсное изображение в Gemini для генерации промпта."""
    print("Отправка изображения в Google Gemini для генерации промпта...")
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        text_prompt_for_gemini = """Your task is to act as a prompt generator for the PhotoMaker AI model. Analyze the provided image in extreme detail. Identify the subject, their clothing, expression, and any specific features.
Describe the background, the lighting style (e.g., golden hour, studio lighting), and the overall artistic style (e.g., photorealistic, illustration).
Your final output must be a single, cohesive text-to-image prompt. This prompt must include the special trigger word 'img' immediately following a class word like 'woman' or 'man'.
For example, the structure must be '...a beautiful woman img...' or '...a handsome man img...'.
Do not add any other text, explanations, or formatting. Just return the single prompt string."""

        response = await model.generate_content_async([text_prompt_for_gemini, reference_image])
        return response.text
    except Exception as e:
        print(f"Произошла ошибка во время вызова Gemini API: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обращении к LLM API: {e}")


# --- ОСНОВНОЙ ЭНДПОИНТ API ---

@router.post("/generate-makeup", response_model=GenerateMakeupResponse, summary="Сгенерировать новое изображение")
async def generate_makeup(request: Request, data: GenerateMakeupRequest): # Убрана зависимость от Firebase для простоты
    """
    Полный конвейер генерации изображений:
    1. Получает промпт от Gemini на основе референсного фото.
    2. Извлекает позу из структурного фото.
    3. Использует лица пользователей для PhotoMaker.
    4. Генерирует и возвращает новое изображение.
    """
    # Доступ к моделям через состояние приложения FastAPI
    MODELS = request.app.state.MODELS
    if not MODELS:
        raise HTTPException(status_code=503, detail="Модели еще не загружены, попробуйте через минуту.")

    # --- Шаг 1: Получение промпта от LLM ---
    try:
        reference_image = download_image(data.reference_photo_url)
        prompt = await get_prompt_from_llm(reference_image)
        print(f"✅ Промпт от LLM получен: '{prompt}'")
    except HTTPException as e:
        raise e

    # --- Шаг 2: Подготовка данных для генерации ---
    print("Подготовка данных для PhotoMaker и ControlNet...")
    pipe = MODELS["pipe"]
    face_detector = MODELS["face_detector"]
    openpose = MODELS["openpose"]

    try:
        pose_image = download_image(data.structure_photo_url)
        input_id_images = [download_image(url) for url in data.user_id_photo_urls]
        
        # Обработка позы
        pose_image = openpose(pose_image, detect_resolution=512, image_resolution=1024)

        # Обработка лиц для PhotoMaker
        id_embed_list = []
        for img in input_id_images:
            faces = face_detector.get(np.array(img))
            if faces:
                id_embed_list.append(torch.from_numpy(faces[0]['embedding']))
        
        if not id_embed_list:
            raise ValueError("Лица не найдены ни на одной из предоставленных фотографий пользователя.")
        
        id_embeds = torch.stack(id_embed_list).to(MODELS["device"])

    except (ValueError, HTTPException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # --- Шаг 3: Генерация изображения ---
    print("Запуск генерации изображения...")
    images = pipe(
        prompt=prompt,
        negative_prompt="photograph, realistic, photo, 3d, render, blurry, deformed, bad anatomy, disfigured, poorly drawn face, mutation, extra limb, ugly, poorly drawn hands, watermark, signature, text, caption",
        input_id_images=input_id_images,
        id_embeds=id_embeds,
        controlnet_conditioning_scale=1.0,
        image=pose_image,
        num_images_per_prompt=1, 
        start_merge_step=1,
        guidance_scale=7,
    ).images
    print("✅ Генерация завершена.")

    # --- Шаг 4: Кодирование результата и возврат ---
    generated_image = images[0]
    buffer = io.BytesIO()
    generated_image.save(buffer, format="JPEG")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return GenerateMakeupResponse(
        message="Изображение успешно сгенерировано",
        llm_prompt=prompt,
        image_base64=base64_image
    )