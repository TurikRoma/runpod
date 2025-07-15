# models.py

from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional

class GenerateMakeupRequest(BaseModel):
    """
    Модель запроса, четко разделяющая фотографии по их назначению
    в конвейере генерации изображений.
    """
    reference_photo_url: HttpUrl = Field(
        ...,
        description="URL фото для отправки в Gemini для генерации промпта."
    )
    structure_photo_url: HttpUrl = Field(
        ...,
        description="URL фото для ControlNet для извлечения позы."
    )
    user_id_photo_urls: List[HttpUrl] = Field(
        ...,
        min_items=1,
        max_items=3,
        description="Список URL-адресов фотографий лица для PhotoMaker."
    )

class GenerateMakeupResponse(BaseModel):
    """
    Модель ответа, возвращающая сгенерированное изображение в формате Base64
    и текстовый промпт, использованный для его создания.
    """
    message: str
    llm_prompt: str
    image_base64: str