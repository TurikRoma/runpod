from fastapi import APIRouter, HTTPException, Depends, Request
from .models import GenerateMakeupRequest, GenerateMakeupResponse, DownloadResult # ОБНОВЛЕНО: импортируем DownloadResult
from firebase_admin import auth

# --- Добавляем импорты для скачивания и работы с изображениями ---
import requests
from PIL import Image
from io import BytesIO
import random
# ---------------------------------------------------------------

router = APIRouter()

async def get_current_user(request: Request):
    """
    Зависимость FastAPI для проверки Firebase ID Token.
    Извлекает токен из заголовка Authorization и верифицирует его через Firebase Admin SDK.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing token')
    
    id_token = auth_header.split(' ')[1]
    
    try:
        # Проверяем Firebase ID Token. Если токен невалиден или просрочен,
        # Firebase Admin SDK вызовет исключение.
        decoded_token = auth.verify_id_token(id_token)
        # Если токен валиден, возвращаем UID пользователя
        return decoded_token['uid']
    except Exception as e:
        # Логируем ошибку для отладки на сервере
        print(f"Firebase token verification failed: {e}") 
        # Возвращаем 401 ошибку клиенту
        raise HTTPException(status_code=401, detail=f'Invalid token: {e}')

# --- Вспомогательная функция для скачивания и обработки одного изображения ---
def download_and_process_image(url: str) -> DownloadResult:
    """
    Скачивает изображение по URL и пытается обработать его с помощью Pillow.
    Возвращает объект DownloadResult с информацией о статусе.
    """
    try:
        # 1. Отправляем GET запрос для скачивания файла
        # stream=True - хорошая практика для больших файлов, timeout - для предотвращения зависаний
        response = requests.get(url, stream=True, timeout=30) # Таймаут 30 секунд
        response.raise_for_status() # Выбросит исключение для HTTP ошибок (4xx, 5xx)

        image_bytes = response.content
        
        # 2. Пытаемся открыть изображение с помощью Pillow.
        # Image.open() может вызвать исключение, если данные не являются валидным изображением.
        image = Image.open(BytesIO(image_bytes))
        
        # Если все успешно, возвращаем результат успеха
        return DownloadResult(
            url=url,
            status="success",
            image_size=[image.width, image.height] # Pillow возвращает (ширина, высота)
        )
    except requests.exceptions.RequestException as e:
        # Ошибки, связанные с HTTP запросом (сеть, DNS, таймаут, 404, 500 и т.д.)
        return DownloadResult(
            url=url,
            status="error",
            error_message=f"Network or HTTP error during download: {type(e).__name__} - {e}"
        )
    except Exception as e:
        # Любые другие ошибки (например, Pillow не смог открыть файл, или файл поврежден)
        return DownloadResult(
            url=url,
            status="error",
            error_message=f"Image processing error: {type(e).__name__} - {e}"
        )

# --- ГЛАВНЫЙ ЭНДПОИНТ API ---
@router.post("/generate-makeup", response_model=GenerateMakeupResponse)
async def generate_makeup(request: GenerateMakeupRequest, user_id: str = Depends(get_current_user)):
    """
    Генерирует макияж на основе фотографий пользователя и референсного фото.
    Скачивает каждое изображение по URL и возвращает общее количество и один случайный URL.
    """
    print(f"Запрос /generate-makeup от пользователя: {user_id}")
    
    all_photos_to_process = []
    all_photos_to_process.extend(request.user_photos)
    all_photos_to_process.append(request.reference_photo)

    processed_urls_only = [] # Для сбора только URL успешно обработанных фото
    
    for url_string in all_photos_to_process:
        print(f"Attempting to download and process: {url_string}")
        result = download_and_process_image(url_string) # Функция остается, но результат используется иначе
        
        if result.status == "success":
            print(f"Successfully processed {url_string}. Size: {result.image_size}")
            processed_urls_only.append(result.url) # Собираем только URL успешно скачанных фото
        else:
            print(f"Failed to process {url_string}. Error: {result.error_message}")

    total_photos_count = len(all_photos_to_process) # Количество полученных URL
    
    # --- НОВАЯ ЛОГИКА: Выбираем случайный URL из успешно обработанных ---
    selected_result_image_url = None
    if processed_urls_only: # Если есть хотя бы одна успешно обработанная фотография
        selected_result_image_url = random.choice(processed_urls_only)
        print(f"Randomly selected final image URL: {selected_result_image_url}")
    else:
        print("No photos were successfully processed, cannot select a random one.")
        # selected_result_image_url останется None, как и определено в модели Optional[HttpUrl]

    # Формируем и возвращаем ответ, используя ОБНОВЛЕННУЮ модель GenerateMakeupResponse
    response = GenerateMakeupResponse(
        total_photos_received=total_photos_count, # Общее количество полученных URL
        result_image=selected_result_image_url,    # Случайный URL или None
    )
    return response