import torch
import numpy as np
import base64
import io
import requests
import google.generativeai as genai
import os
import time # <-- Добавлено для замера времени

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import HttpUrl
from PIL import Image
from firebase_admin import auth

from .models import GenerateMakeupRequest, GenerateMakeupResponse

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY environment variable not set!")
else:
    genai.configure(api_key=GEMINI_API_KEY)
    print("[INFO] Google Gemini configured successfully.")

router = APIRouter()

async def get_current_user(request: Request):
    # ... (ваш код без изменений) ...
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing token')
    id_token = auth_header.split(' ')[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        print(f"[DEBUG] User authenticated successfully: {decoded_token['uid']}")
        return decoded_token['uid']
    except Exception as e:
        print(f"[ERROR] Firebase token verification failed: {e}")
        raise HTTPException(status_code=401, detail=f'Invalid token: {e}')

def download_image(url: HttpUrl) -> Image.Image:
    """Скачивает изображение по URL и возвращает объект PIL Image."""
    try:
        print(f"[DEBUG] Downloading image from: {str(url)[:100]}...") # Логируем URL
        response = requests.get(str(url), stream=True, timeout=30) # Увеличим таймаут на всякий случай
        response.raise_for_status()
        image = Image.open(io.BytesIO(response.content)).convert("RGB")
        print(f"[DEBUG] Image downloaded successfully.")
        return image
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to download image. URL: {url}. Error: {e}")
        raise HTTPException(status_code=400, detail=f"Не удалось скачать изображение по URL: {url}. Ошибка: {e}")

async def get_prompt_from_llm(reference_image: Image.Image) -> str:
    """Отправляет референсное изображение в Gemini для генерации промпта."""
    print("[DEBUG] Sending image to Google Gemini for prompt generation...")
    try:
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        text_prompt_for_gemini = """Your task is to act as a prompt generator for the PhotoMaker AI model. Analyze the provided image in extreme detail. Identify the subject, their clothing, expression, and any specific features.
Describe the background, the lighting style (e.g., golden hour, studio lighting), and the overall artistic style (e.g., photorealistic, illustration).
Your final output must be a single, cohesive text-to-image prompt. This prompt must include the special trigger word 'img' immediately following a class word like 'woman' or 'man'.
For example, the structure must be '...a beautiful woman img...' or '...a handsome man img...'.
Do not add any other text, explanations, or formatting. Just return the single prompt string."""

        response = await model.generate_content_async([text_prompt_for_gemini, reference_image])
        print("[DEBUG] Received prompt from Gemini successfully.")
        return response.text
    except Exception as e:
        print(f"[ERROR] An error occurred during Gemini API call: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при обращении к LLM API: {e}")

@router.post("/generate-makeup", response_model=GenerateMakeupResponse, summary="Сгенерировать новое изображение")
async def generate_makeup(request: Request, data: GenerateMakeupRequest, user_id: str = Depends(get_current_user)):
    
    start_time = time.time()
    print("\n" + "="*50)
    print(f"[INFO] Received new /generate-makeup request for user {user_id}")
    print("="*50 + "\n")

    MODELS = request.app.state.MODELS
    if not MODELS:
        print("[ERROR] Models not found in app.state. They might still be loading.")
        raise HTTPException(status_code=503, detail="Модели еще не загружены, попробуйте через минуту.")
    print("[DEBUG] Models are loaded and accessible from app.state.")

    # --- Шаг 1: Получение промпта от LLM ---
    try:
        print("[DEBUG] Step 1: Getting prompt from LLM...")
        reference_image = download_image(data.reference_photo_url)
        prompt = await get_prompt_from_llm(reference_image)
        print(f"[INFO] Generated prompt: {prompt}")
    except HTTPException as e:
        raise e

    # --- Шаг 2: Подготовка данных для генерации ---
    print("[DEBUG] Step 2: Preparing data for PhotoMaker and ControlNet...")
    pipe = MODELS["pipe"]
    face_detector = MODELS["face_detector"]
    openpose = MODELS["openpose"]

    try:
        print("[DEBUG] Downloading pose image...")
        pose_image = download_image(data.structure_photo_url)
        print("[DEBUG] Downloading user ID images...")
        input_id_images = [download_image(url) for url in data.user_id_photo_urls]
        print(f"[DEBUG] Downloaded {len(input_id_images)} user ID images.")
        
        # Обработка позы
        print("[DEBUG] Processing pose with Openpose...")
        pose_image = openpose(pose_image, detect_resolution=512, image_resolution=1024)
        print("[DEBUG] Pose processed successfully.")

        # Обработка лиц для PhotoMaker
        print("[DEBUG] Processing faces with FaceAnalysis...")
        id_embed_list = []
        for i, img in enumerate(input_id_images):
            print(f"[DEBUG]  - Analyzing face in user image #{i+1}...")
            faces = face_detector.get(np.array(img))
            if faces:
                print(f"[DEBUG]  - Face found in image #{i+1}.")
                id_embed_list.append(torch.from_numpy(faces[0]['embedding']))
            else:
                print(f"[WARNING] - No face found in image #{i+1}.")
        
        if not id_embed_list:
            print("[ERROR] No faces found in any of the provided user photos.")
            raise ValueError("Лица не найдены ни на одной из предоставленных фотографий пользователя.")
        
        print(f"[DEBUG] Found faces in {len(id_embed_list)} images. Stacking embeddings.")
        id_embeds = torch.stack(id_embed_list).to(MODELS["device"])

    except (ValueError, HTTPException) as e:
        print(f"[ERROR] Error during data preparation: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    
    # --- Шаг 3: Генерация изображения ---
    print("\n[INFO] ALL DATA PREPARED. STARTING THE MAIN GENERATION PIPELINE...")
    print("="*20 + " THIS IS THE HEAVY PART " + "="*20)
    generation_start_time = time.time()
    
    try:
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
    except Exception as e:
        print(f"\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(f"[CRITICAL] The main 'pipe()' call failed! Error: {e}")
        print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        # Возможно, здесь нехватка VRAM.
        raise HTTPException(status_code=500, detail=f"Критическая ошибка во время генерации: {e}")

    generation_time = time.time() - generation_start_time
    print(f"[INFO] GENERATION COMPLETED SUCCESSFULLY in {generation_time:.2f} seconds.")
    print("="*58 + "\n")

    # --- Шаг 4: Кодирование результата и возврат ---
    print("[DEBUG] Step 4: Encoding result and returning response...")
    generated_image = images[0]
    buffer = io.BytesIO()
    generated_image.save(buffer, format="JPEG")
    base64_image = base64.b64encode(buffer.getvalue()).decode("utf-8")
    
    total_time = time.time() - start_time
    print(f"[INFO] Request completed successfully in {total_time:.2f} seconds.")
    
    return GenerateMakeupResponse(
        message="Изображение успешно сгенерировано",
        llm_prompt=prompt,
        image_base64=base64_image
    )