
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


def load_models(download_only=False):
    """
    Загружает или скачивает все необходимые модели.
    - В обычном режиме (download_only=False): загружает модели в память/VRAM.
    - В режиме скачивания (download_only=True): только скачивает файлы в кэш, не загружая их в память.
    """
    print("Начало загрузки/скачивания моделей...")

    # --- 1. Определение "ссылок" на модели ---
    photomaker_repo_id = "TencentARC/PhotoMaker-V2"
    openpose_repo_id = "lllyasviel/ControlNet"
    controlnet_repo_id = "thibaud/controlnet-openpose-sdxl-1.0"
    base_model_repo_id = "SG161222/RealVisXL_V4.0"
    
    # --- 2. Создание папки для хранения кэша ---
    LOCAL_CACHE_DIR = "./models_cache"
    print(f"Создание или проверка папки для кэша: {os.path.abspath(LOCAL_CACHE_DIR)}")
    os.makedirs(LOCAL_CACHE_DIR, exist_ok=True)

    # --- Определение устройства и типа данных ---
    if download_only:
        device = "cpu"
        torch_dtype = torch.float32  # Для скачивания не важен тип, но float32 самый безопасный
        print("[DOWNLOAD-ONLY MODE] Устройство: cpu, Тип: float32.")
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
        print(f"Используемое устройство: {device}, Тип: {torch_dtype}")
    
    # --- 3. Загрузка/скачивание компонентов ---

    # FaceAnalysis
    # В режиме скачивания достаточно просто создать объект, он сам скачает что нужно при первом вызове.
    # Но для надежности вызовем prepare с CPU провайдером.
    print("Загрузка/скачивание FaceAnalysis...")
    providers = ['CPUExecutionProvider'] if download_only else ['CUDAExecutionProvider', 'CPUExecutionProvider']
    face_detector = FaceAnalysis2(providers=providers, allowed_modules=['detection', 'recognition'])
    face_detector.prepare(ctx_id=0, det_size=(640, 640))
    
    # PhotoMaker weights
    print("Загрузка/скачивание PhotoMaker v2 weights...")
    photomaker_path = hf_hub_download(
        repo_id=photomaker_repo_id,
        filename="photomaker-v2.bin",
        repo_type="model",
        cache_dir=LOCAL_CACHE_DIR
    )

    # OpenPose
    print("Загрузка/скачивание OpenPose detector...")
    openpose = OpenposeDetector.from_pretrained(openpose_repo_id, cache_dir=LOCAL_CACHE_DIR)

    # ControlNet
    print("Загрузка/скачивание ControlNet model...")
    controlnet_pose = ControlNetModel.from_pretrained(
        controlnet_repo_id,
        torch_dtype=torch_dtype,
        cache_dir=LOCAL_CACHE_DIR
    )
    if not download_only:
        controlnet_pose.to(device)

    # Base Model Pipeline
    print("Загрузка/скачивание основного пайплайна Stable Diffusion...")
    pipe = PhotoMakerStableDiffusionXLPipeline.from_pretrained(
        base_model_repo_id,
        # В режиме скачивания мы не передаем controlnet, чтобы не создавать лишних объектов
        controlnet=controlnet_pose if not download_only else None,
        torch_dtype=torch_dtype,
        cache_dir=LOCAL_CACHE_DIR
    )

    if download_only:
        print("Все модели успешно СКАЧАНЫ в кэш.")
        return None # В режиме скачивания ничего не возвращаем

    # --- Сборка пайплайна для рабочего режима ---
    print("Сборка и настройка рабочего пайплайна...")
    pipe.controlnet = controlnet_pose # Явно присваиваем controlnet
    pipe = pipe.to(device)

    pipe.load_photomaker_adapter(
        os.path.dirname(photomaker_path),
        subfolder="",
        weight_name=os.path.basename(photomaker_path),
        trigger_word="img"
    )

    pipe.fuse_lora()
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    pipe.enable_model_cpu_offload() # Важно для экономии VRAM
    
    print("Модели успешно загружены и готовы к работе!")

    return {
        "pipe": pipe,
        "face_detector": face_detector,
        "openpose": openpose,
        "device": device
    }