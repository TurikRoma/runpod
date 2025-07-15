from pydantic import BaseModel, validator
from typing import List
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

class GenerateMakeupResponse(BaseModel):
    total_photos: int
    user_photos: List[str]
    reference_photo: str
    message: str 