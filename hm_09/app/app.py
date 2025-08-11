from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class ModelInferenceOutput(BaseModel):
    result: float


@app.get("/")
def index():
    return {"text": "ML model inference"}


@app.get("/analysis/{data}", response_model=ModelInferenceOutput)
def run_model_analysis(data: str):
    result = sum(map(data.lower().count, "aeiuyo")) / len(data)
    return {"result": result}
