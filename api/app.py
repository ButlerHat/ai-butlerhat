# Create a FastAPI app with a post route that receives an image and a prompt and returns an action prediction with a huggingface model
import io
import base64
import sys
import time
from contextlib import asynccontextmanager
from typing import List
import PIL.Image
from pydantic import BaseModel
from pydantic_settings import BaseSettings  # pylint: disable=E0401  # type: ignore
from fastapi.responses import JSONResponse
from fastapi import FastAPI, UploadFile, Form, HTTPException
from ButlerRobot.src.data_to_ai.data_types import PromptStep
from core.datasets.robotframework import AlfredExampleToInstruction
from core.models import AlfredUnimodelForConditionalGeneration, AlfredTokenizer, AlfredPipeline

# Print python version
print(sys.version)

class Config(BaseSettings):
    """
    Config class to parse the config with argparse.
    """
    host: str = "0.0.0.0"
    port: int = 5000
    name_or_path: str = "/workspaces/ai-butlerhat/data-butlerhat/robotframework-butlerhat/TestSuites/CicloZero/ai_finetuned/model"

# Define your resources as None initially
settings = Config().model_dump()
model = None
tokenizer = None
alfred_pipeline = None


class PredictionRequest(BaseModel):
    """
    Class to accpet the request to the predict_rf endpoint.
    """
    image: str
    instruction_history: List[dict]


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, tokenizer, alfred_pipeline
    model = AlfredUnimodelForConditionalGeneration.from_pretrained(settings["name_or_path"])
    tokenizer = AlfredTokenizer.from_pretrained(settings["name_or_path"])
    alfred_pipeline = AlfredPipeline(model=model, tokenizer=tokenizer, device=0)
    yield
    # Shutdown logic here

app = FastAPI(lifespan=lifespan)


@app.get('/auth')
def auth():
    """
    Auth endpoint to restrict access to the API.
    """
    return JSONResponse(content={"auth": True})

@app.get('/health')
def health():
    """
    Health endpoint to check if the API is running.
    """
    return JSONResponse(content={"health": True})

@app.post('/predict')
async def predict(image: UploadFile = Form(...), instruction: str = Form(...)):
    """
    Predict endpoint to predict an action from an image and a prompt.
    """
    # Parse image to pil image
    if alfred_pipeline is None:
        raise HTTPException(status_code=500, detail="Model not loaded")
    image_content = await image.read()
    image_pil = PIL.Image.open(io.BytesIO(image_content)).convert("RGB")
    prediction = alfred_pipeline({"image":image_pil, "instruction":instruction})

    # Return the action
    return JSONResponse(content={"action": prediction})

@app.post('/predict_rf')
async def predict_rf(request: PredictionRequest):
    """
    Predict endpoint to predict an action from an image and a prompt.
    """
    if tokenizer is None or alfred_pipeline is None:
        raise HTTPException(status_code=500, detail="Model not loaded")

    # Parse the image from base64 to pil image
    image_pil = PIL.Image.open(io.BytesIO(base64.b64decode(request.image))).convert("RGB")
    
    # Parse the instruction history to a prompt
    instruction_history_d: list[dict] = request.instruction_history
    instruction_history: list[PromptStep] = [PromptStep.from_dict(step) for step in instruction_history_d]
    print(instruction_history)
    
    t_init = time.time()
    prompt = AlfredExampleToInstruction(
                tokenizer, image_pil.size
            ).build(instruction_history)
    elapsed_time = time.time() - t_init
    print(f"Time to build prompt: {elapsed_time}")
    
    print(prompt)
    # Get time that takes to predict
    t_init = time.time()
    prediction = alfred_pipeline({"image":image_pil, "instruction":prompt})
    elapsed_time = time.time() - t_init
    print(f'Prediction: {prediction}')
    print(f"Time to predict: {elapsed_time}")

    # Return the action
    return JSONResponse(content={"action": prediction})

# Run the app
if __name__ == "__main__":
    
    # Run the app with uvicorn (ASGI server)
    import uvicorn
    uvicorn.run(app, host=settings["host"], port=settings["port"])  # type: ignore
