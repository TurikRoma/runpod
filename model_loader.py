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

# --- ВОЗВРАЩАЕМ ИМПОРТЫ ДЛЯ FaceAnalysis2 ---
from photomaker import FaceAnalysis2, analyze_faces

def load_models():
    """
    Загружает все необходимые модели в память и возвращает их в виде словаря.
    Эта функция должна вызываться только один раз при старте сервиса.
    """
    print("Начало загрузки моделей в память из предзагруженного кэша...")

    # --- 1. Определение "ссылок" на модели ---
    photomaker_repo_id = "TencentARC/PhotoMaker-V2"
    openpose_repo_id = "lllyasviel/ControlNet"
    controlnet_repo_id = "thibaud/controlnet-openpose-sdxl-1.0"
    base_model_repo_id = "SG161222/RealVisXL_V4.0"

    # --- 2. Указываем ГЛОБАЛЬНУЮ папку для кэша, которая используется в Dockerfile ---
    CACHE_DIR = "/root/.cache/huggingface/hub"
    print(f"Проверка наличия кэша в папке: {CACHE_DIR}")

    # --- Определение устройства ---
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Используемое устройство: {device}")
    torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16

    # --- 3. Загрузка компонентов с использованием глобального кэша ---

    # --- ИСПОЛЬЗУЕМ FaceAnalysis2, КАК ВЫ УКАЗАЛИ ---
    # Добавляем 'CPUExecutionProvider' как запасной вариант для стабильности
    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    face_detector = FaceAnalysis2(providers=providers, allowed_modules=['detection', 'recognition'])
    face_detector.prepare(ctx_id=0, det_size=(640, 640))
    # Модели для insightface ('buffalo_l') уже должны быть в /root/.insightface/models/ благодаря Dockerfile

    photomaker_path = hf_hub_download(
        repo_id=photomaker_repo_id,
        filename="photomaker-v2.bin",
        repo_type="model",
        cache_dir=CACHE_DIR
    )

    openpose = OpenposeDetector.from_pretrained(openpose_repo_id, cache_dir=CACHE_DIR)

    controlnet_pose = ControlNetModel.from_pretrained(
        controlnet_repo_id,
        torch_dtype=torch_dtype,
        cache_dir=CACHE_DIR
    ).to(device)

    # --- Сборка основного пайплайна из кэшированных компонентов ---
    pipe = PhotoMakerStableDiffusionXLPipeline.from_pretrained(
        base_model_repo_id,
        controlnet=controlnet_pose,
        torch_dtype=torch_dtype,
        cache_dir=CACHE_DIR
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

    return {
        "pipe": pipe,
        "face_detector": face_detector,
        "openpose": openpose,
        "device": device
    }