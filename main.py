from fastapi import FastAPI

app = FastAPI()

@app.get("/", status_code=200)
def read_root():
    return {"message": "Hello World"}

@app.get("/healthz", status_code=200)
def health_check():
    return {"status": "ok"}