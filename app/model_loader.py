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
    print("🚀 Начало загрузки моделей в память...")

    CACHE_DIR = "/workspace/huggingface_cache"
    device = "cuda"
    torch_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16

    # --- Загрузка компонентов пайплайна ---
    face_detector = FaceAnalysis2(providers=['CUDAExecutionProvider'], allowed_modules=['detection', 'recognition'])
    face_detector.prepare(ctx_id=0, det_size=(640, 640))

    photomaker_path = hf_hub_download(
        repo_id="TencentARC/PhotoMaker-V2",
        filename="photomaker-v2.bin",
        repo_type="model",
        cache_dir=CACHE_DIR
    )

    openpose = OpenposeDetector.from_pretrained("lllyasviel/ControlNet", cache_dir=CACHE_DIR)

    controlnet_pose = ControlNetModel.from_pretrained(
        "thibaud/controlnet-openpose-sdxl-1.0",
        torch_dtype=torch_dtype,
        cache_dir=CACHE_DIR
    ).to(device)

    # --- Сборка основного пайплайна ---
    pipe = PhotoMakerStableDiffusionXLPipeline.from_pretrained(
        "SG161222/RealVisXL_V4.0",
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
    
    print("✅ Модели успешно загружены!")

    # Возвращаем все необходимые объекты
    return {
        "pipe": pipe,
        "face_detector": face_detector,
        "openpose": openpose,
        "device": device
    }