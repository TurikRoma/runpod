from fastapi import APIRouter, HTTPException, Depends, Request
from .models import GenerateMakeupRequest, GenerateMakeupResponse
from firebase_admin import auth

router = APIRouter()

async def get_current_user(request: Request):
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        raise HTTPException(status_code=401, detail='Missing token')
    id_token = auth_header.split(' ')[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token['uid']
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid token')

@router.post("/generate-makeup", response_model=GenerateMakeupResponse)
async def generate_makeup(request: GenerateMakeupRequest, user_id: str = Depends(get_current_user)):
    """
    Generate makeup based on user photos and reference photo
    """
    print(f"Запрос от пользователя: {user_id}")
    print(f"Фото: {request.user_photos}")
    print(f"Референс: {request.reference_photo}")
    total_photos = len(request.user_photos) + 1
    response = GenerateMakeupResponse(
        total_photos=total_photos,
        user_photos=request.user_photos,
        reference_photo=request.reference_photo,
        message=f"Received {total_photos} photos successfully"
    )
    return response 