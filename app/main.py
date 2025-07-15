import torch
import numpy as np
import base64
import io
import requests
import os
import google.generativeai as genai

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, Field
from PIL import Image
from diffusers.utils import load_image

# Локальные импорты
from model_loader import load_models

app = FastAPI(title="AI MakeUp API", version="2.0")
    
API_KEY = "AIzaSyDYLAICEELK0VG1FjOunEPgasvwJUSRyOU"

genai.configure(api_key=API_KEY)

MODELS = {}

@app.on_event("startup")
def startup_event():
    MODELS.update(load_models())
    print("Сервер готов к приему запросов.")

class GenerationRequest(BaseModel):
    """
    Обновленная модель запроса. Теперь принимает три разных типа фото.
    """
    reference_photo_url: HttpUrl = Field(
        ...,
        description="URL фото для отправки в LLM для генерации промпта."
    )
    structure_photo_url: HttpUrl = Field(
        ...,
        description="URL фото для ControlNet, чтобы взять позу."
    )
    user_id_photo_urls: list[HttpUrl] = Field(
        ...,
        description="Список URL фото лица для PhotoMaker."
    )

def download_image(url: str):
    """Скачивает изображение по URL и возвращает объект PIL Image."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        return image
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Не удалось скачать изображение по URL: {url}. Ошибка: {e}")

# --- НОВАЯ ФУНКЦИЯ: Интеграция с LLM ---

async def get_prompt_from_llm(reference_image: Image.Image) -> str:

    print("Отправка изображения в Google Gemini...")
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')

        # Текстовая часть промпта, которая инструктирует модель
        text_prompt_for_gemini = """Your task is to act as a prompt generator for the PhotoMaker AI model. Analyze the provided image in extreme detail. Identify the subject, their clothing, expression, and any specific features.
Describe the background, the lighting style (e.g., golden hour, studio lighting), and the overall artistic style (e.g., photorealistic, illustration). 
Your final output must be a single, cohesive text-to-image prompt. This prompt must include the special trigger word 'img' immediately following a class word like 'woman' or 'man'.
For example, the structure must be '...a beautiful woman img...' or '...a handsome man img...'. 
Do not add any other text, explanations, or formatting. Just return the single prompt string."""
        
        # Собираем промпт из текста и изображения
        prompt_parts = [text_prompt_for_gemini, reference_image]
        
        # Генерируем контент
        response = model.generate_content(prompt_parts)
        
        return response.text

    except Exception as e:
        print(f"Произошла ошибка во время вызова Gemini API: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обращении к LLM API: {e}")

@app.post("/generate", summary="Сгенерировать новое изображение с помощью LLM-промпта")
async def generate_image(request: GenerationRequest):
    if not MODELS:
        raise HTTPException(status_code=503, detail="Модели еще не загружены, попробуйте через минуту.")

    # --- Шаг 1: Скачиваем референсное фото и получаем промпт от LLM ---
    try:
        reference_image = download_image(str(request.reference_photo_url))
        prompt = await get_prompt_from_llm(reference_image)
        print(f"✅ Промпт от LLM получен: '{prompt}'")
    except HTTPException as e:
        raise e # Передаем ошибку клиенту, если она произошла

    # --- Шаг 2: Подготовка данных для модели генерации ---
    print("Подготовка данных для PhotoMaker...")
    pipe = MODELS["pipe"]
    face_detector = MODELS["face_detector"]
    openpose = MODELS["openpose"]

    try:
        pose_image = download_image(str(request.structure_photo_url))
        input_id_images = [download_image(str(url)) for url in request.user_id_photo_urls]
        
        pose_image = openpose(pose_image, detect_resolution=512, image_resolution=1024)

        id_embed_list = []
        for img in input_id_images:
            img_np = np.array(img)
            faces = face_detector.get(img_np)
            if faces:
                id_embed_list.append(torch.from_numpy(faces[0]['embedding']))
        
        if not id_embed_list:
            raise ValueError("Лица не найдены на входных ID-изображениях.")
        
        id_embeds = torch.stack(id_embed_list)

    except (ValueError, HTTPException) as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # --- Шаг 3: Генерация изображения ---
    print("Запуск генерации с использованием LLM-промпта...")
    images = pipe(
        prompt=prompt,
        negative_prompt="photograph, realistic, photo, 3d, render, blurry, deformed, bad anatomy, disfigured, poorly drawn face, mutation, extra limb, ugly, poorly drawn hands, watermark, signature",
        input_id_images=input_id_images,
        id_embeds=id_embeds,
        controlnet_conditioning_scale=1.0,
        image=pose_image,
        num_images_per_prompt=3,
        start_merge_step=1,
        guidance_scale=7,
    ).images
    print("Генерация завершена.")

    # --- Шаг 4: Кодирование результата и возврат ---
    generated_image = images[0]
    buffer = io.BytesIO()
    generated_image.save(buffer, format="JPEG")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return {
        "message": "Изображение успешно сгенерировано с помощью LLM",
        "llm_prompt": prompt,
        "image_base64": base64_image
    }