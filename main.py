from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/", status_code=200)
def read_root():
    """
    Это наш тестовый эндпоинт.
    Он будет вызываться при GET запросе на корень нашего сервера.
    """
    return {"message": "Hello World"}

# Этот эндпоинт нужен для проверки "жизни" сервера самим RunPod
@app.get("/healthz", status_code=200)
def health_check():
    return {"status": "ok"}