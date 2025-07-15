import os
import sys

from pathlib import Path
from PIL import Image

import numpy as np
import torch
from diffusers.utils import load_image
from diffusers import EulerDiscreteScheduler, ControlNetModel

from huggingface_hub import hf_hub_download
from controlnet_aux import OpenposeDetector
from photomaker import PhotoMakerStableDiffusionXLPipeline
from photomaker import FaceAnalysis2, analyze_faces

def load_models():
    """
    Загружает все необходимые модели в память и возвращает их в виде словаря.
    Эта функция должна вызываться только один раз при старте сервиса.
    """
    print("Начало загрузки моделей в память...")

    # --- 1. Определение "ссылок" на модели ---
    photomaker_repo_id = "TencentARC/PhotoMaker-V2"
    openpose_repo_id = "lllyasviel/ControlNet"
    controlnet_repo_id = "thibaud/controlnet-openpose-sdxl-1.0"
    base_model_repo_id = "SG161222/RealVisXL_V4.0"
    
    # --- 2. Создание папки для хранения кэша ---
    LOCAL_CACHE_DIR = "./models_cache"
    print(f"Создание или проверка папки для кэша: {os.path.abspath(LOCAL_CACHE_DIR)}")
    os.makedirs(LOCAL_CACHE_DIR, exist_ok=True)

    # --- Определение устройства ---
    try:
        if torch.cuda.is_available():
            device = "cuda"
        else:
            device = "cpu"
    except:
        device = "cpu"
    
    print(f"Используемое устройство: {device}")
    torch_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    # --- 3. Загрузка компонентов с использованием локального кэша ---
    face_detector = FaceAnalysis2(providers=['CUDAExecutionProvider'], allowed_modules=['detection', 'recognition'])
    face_detector.prepare(ctx_id=0, det_size=(640, 640))

    photomaker_path = hf_hub_download(
        repo_id=photomaker_repo_id,
        filename="photomaker-v2.bin",
        repo_type="model",
        cache_dir=LOCAL_CACHE_DIR
    )

    openpose = OpenposeDetector.from_pretrained(openpose_repo_id, cache_dir=LOCAL_CACHE_DIR)

    controlnet_pose = ControlNetModel.from_pretrained(
        controlnet_repo_id,
        torch_dtype=torch_dtype,
        cache_dir=LOCAL_CACHE_DIR
    ).to(device)

    # --- Сборка основного пайплайна ---
    pipe = PhotoMakerStableDiffusionXLPipeline.from_pretrained(
        base_model_repo_id,
        controlnet=controlnet_pose,
        torch_dtype=torch_dtype,
        cache_dir=LOCAL_CACHE_DIR
    ).to(device)

    pipe.load_photomaker_adapter(
        os.path.dirname(photomaker_path),
        subfolder="",
        weight_name=os.path.basename(photomaker_path),
        trigger_word="img"
    )

    pipe.fuse_lora()
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.enable_model_cpu_offload()
    
    print("Модели успешно загружены!")

    # Возвращаем все необходимые объекты
    return {
        "pipe": pipe,
        "face_detector": face_detector,
        "openpose": openpose,
        "device": device
    }