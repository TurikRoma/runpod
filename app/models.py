from pydantic import BaseModel, validator,HttpUrl
from typing import List,Union
import re

class GenerateMakeupRequest(BaseModel):
    user_photos: List[str]
    reference_photo: str
    
    @validator('user_photos')
    def validate_user_photos(cls, v):
        if not v:
            raise ValueError('User photos cannot be empty')
        if len(v) > 3:
            raise ValueError('Maximum 3 user photos allowed')
        if len(v) < 1:
            raise ValueError('Minimum 1 user photo required')
        
        # Validate URLs
        for url in v:
            if not re.match(r'^https?://', url):
                raise ValueError(f'Invalid URL format: {url}')
        
        return v
    
    @validator('reference_photo')
    def validate_reference_photo(cls, v):
        if not v:
            raise ValueError('Reference photo cannot be empty')
        if not re.match(r'^https?://', v):
            raise ValueError(f'Invalid URL format: {v}')
        return v

class DownloadResult(BaseModel):
    url: str # Оригинальный URL
    status: str # 'success' или 'error'
    error_message: Union[str, None] = None # Сообщение об ошибке, если статус 'error'
    image_size: Union[List[int], None] = None # Размеры изображения [width, height], если успешно

class GenerateMakeupResponse(BaseModel):
    total_photos_received: int # Общее количество URL, которые были получены
    processed_results: List[DownloadResult] # Результаты обработки каждого URL
    message: str # Общее сообщение о статусе