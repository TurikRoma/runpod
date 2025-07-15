import torch
import os
from diffusers import ControlNetModel, EulerDiscreteScheduler
from controlnet_aux import OpenposeDetector
from photomaker import PhotoMakerStableDiffusionXLPipeline
from huggingface_hub import hf_hub_download
# insightface будет загружен через curl в Dockerfile, т.к. он не с Hugging Face

if __name__ == "__main__":
    # Этот путь должен совпадать с HF_HOME в Dockerfile и cache_dir в model_loader.py
    CACHE_DIR = "/root/.cache/huggingface/hub"
    os.makedirs(CACHE_DIR, exist_ok=True)

    print(f"Начало предзагрузки моделей в кэш: {CACHE_DIR}")

    # --- Определение "ссылок" на модели ---
    photomaker_repo_id = "TencentARC/PhotoMaker-V2"
    openpose_repo_id = "lllyasviel/ControlNet"
    controlnet_repo_id = "thibaud/controlnet-openpose-sdxl-1.0"
    base_model_repo_id = "SG161222/RealVisXL_V4.0"
    
    # Используем float16 для экономии места и VRAM, bfloat16 не всегда поддерживается
    torch_dtype = torch.float16

    # --- 1. Загрузка PhotoMaker адаптера ---
    print(f"Загрузка: {photomaker_repo_id}")
    hf_hub_download(
        repo_id=photomaker_repo_id,
        filename="photomaker-v2.bin",
        repo_type="model",
        cache_dir=CACHE_DIR
    )

    # --- 2. Загрузка Openpose детектора ---
    # from_pretrained скачает все необходимые файлы для Openpose
    print(f"Загрузка: {openpose_repo_id}")
    OpenposeDetector.from_pretrained(openpose_repo_id, cache_dir=CACHE_DIR)

    # --- 3. Загрузка ControlNet модели ---
    # from_pretrained скачает и модель, и ее конфиг
    print(f"Загрузка: {controlnet_repo_id}")
    ControlNetModel.from_pretrained(
        controlnet_repo_id,
        torch_dtype=torch_dtype,
        cache_dir=CACHE_DIR
    )

    # --- 4. Загрузка базовой модели (пайплайна) ---
    # Это самая большая загрузка, from_pretrained позаботится обо всех компонентах
    print(f"Загрузка: {base_model_repo_id}")
    PhotoMakerStableDiffusionXLPipeline.from_pretrained(
        base_model_repo_id,
        torch_dtype=torch_dtype,
        cache_dir=CACHE_DIR,
        # Мы не передаем controlnet здесь, т.к. просто кэшируем компоненты
    )

    print("Все модели успешно предзагружены в кэш!")