import os
import sys
import time
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
    print(f"--- [model_loader] STARTING load_models(download_only={download_only}) ---")
    start_time = time.time()

    # --- 1. Определение "ссылок" на модели ---
    photomaker_repo_id = "TencentARC/PhotoMaker-V2"
    openpose_repo_id = "lllyasviel/ControlNet"
    controlnet_repo_id = "thibaud/controlnet-openpose-sdxl-1.0"
    base_model_repo_id = "SG161222/RealVisXL_V4.0"
    
    # --- 2. Создание папки для хранения кэша ---
    LOCAL_CACHE_DIR = "./models_cache"
    print(f"--- [model_loader] Cache directory: {os.path.abspath(LOCAL_CACHE_DIR)}")
    os.makedirs(LOCAL_CACHE_DIR, exist_ok=True)

    # --- Определение устройства и типа данных ---
    if download_only:
        device = "cpu"
        torch_dtype = torch.float32
        print(f"--- [model_loader] DOWNLOAD-ONLY MODE. Device: {device}, DType: {torch_dtype}")
    else:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        torch_dtype = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
        print(f"--- [model_loader] RUNTIME MODE. Device: {device}, DType: {torch_dtype}")
    
    # --- 3. Загрузка/скачивание компонентов ---

    print("\n--- [model_loader] Step 1/5: Loading FaceAnalysis...")
    providers = ['CPUExecutionProvider'] if download_only else ['CUDAExecutionProvider', 'CPUExecutionProvider']
    face_detector = FaceAnalysis2(providers=providers, allowed_modules=['detection', 'recognition'])
    face_detector.prepare(ctx_id=0, det_size=(640, 640))
    print("--- [model_loader] FaceAnalysis loaded. OK.")
    
    print("\n--- [model_loader] Step 2/5: Loading PhotoMaker weights...")
    photomaker_path = hf_hub_download(
        repo_id=photomaker_repo_id,
        filename="photomaker-v2.bin",
        repo_type="model",
        cache_dir=LOCAL_CACHE_DIR
    )
    print("--- [model_loader] PhotoMaker weights loaded. OK.")

    print("\n--- [model_loader] Step 3/5: Loading OpenPose detector...")
    openpose = OpenposeDetector.from_pretrained(openpose_repo_id, cache_dir=LOCAL_CACHE_DIR)
    print("--- [model_loader] OpenPose detector loaded. OK.")

    print("\n--- [model_loader] Step 4/5: Loading ControlNet model...")
    controlnet_pose = ControlNetModel.from_pretrained(
        controlnet_repo_id,
        torch_dtype=torch_dtype,
        cache_dir=LOCAL_CACHE_DIR
    )
    print("--- [model_loader] ControlNet model loaded from disk. OK.")
    if not download_only:
        print("--- [model_loader] Moving ControlNet to device...")
        controlnet_pose.to(device)
        print("--- [model_loader] ControlNet moved to device. OK.")

    print("\n--- [model_loader] Step 5/5: Loading Base Pipeline (this is the heaviest)...")
    pipe = PhotoMakerStableDiffusionXLPipeline.from_pretrained(
        base_model_repo_id,
        controlnet=controlnet_pose if not download_only else None,
        torch_dtype=torch_dtype,
        cache_dir=LOCAL_CACHE_DIR
    )
    print("--- [model_loader] Base Pipeline loaded from disk. OK.")

    if download_only:
        print(f"--- [model_loader] DOWNLOAD-ONLY finished in {time.time() - start_time:.2f}s. ---")
        return None

    # --- Сборка пайплайна для рабочего режима ---
    print("\n--- [model_loader] Finalizing pipeline setup...")
    print("--- [model_loader] Attaching ControlNet...")
    pipe.controlnet = controlnet_pose
    print("--- [model_loader] Moving pipeline to device...")
    pipe = pipe.to(device)
    print("--- [model_loader] Loading PhotoMaker adapter...")
    pipe.load_photomaker_adapter(
        os.path.dirname(photomaker_path),
        subfolder="",
        weight_name=os.path.basename(photomaker_path),
        trigger_word="img"
    )
    print("--- [model_loader] Fusing LoRA...")
    pipe.fuse_lora()
    print("--- [model_loader] Setting scheduler...")
    pipe.scheduler = EulerDiscreteScheduler.from_config(pipe.scheduler.config)
    print("--- [model_loader] Enabling CPU offload...")
    pipe.enable_model_cpu_offload()
    
    print(f"--- [model_loader] ALL MODELS LOADED SUCCESSFULLY in {time.time() - start_time:.2f}s. ---")

    return {
        "pipe": pipe,
        "face_detector": face_detector,
        "openpose": openpose,
        "device": device
    }