# Create a flask app with a post route that recives a image and a prompt and returns a action prediction with a huggingface model
import flask
import io
import base64
import PIL.Image
import time
from transformers import HfArgumentParser
from dataclasses import dataclass
from core.datasets.robotframework import AlfredExampleToInstruction
from core.models import AlfredUnimodelForConditionalGeneration, AlfredTokenizer, AlfredPipeline
from src.qact.data_structure import PromptStep


app = flask.Flask(__name__)
# app.config["DEBUG"] = True


@dataclass
class ModelConfig:
    model_name_or_path: str = "/workspaces/ia-butlerhat/data-butlerhat/robotframework-butlerhat/TestSuites/CicloZero/ai_finetuned/model"

@dataclass
class FlaskConfig:
    host: str = "0.0.0.0"
    port: int = 5000


@app.route('/predict', methods=['POST'])
def predict():
    # Get the image and prompt
    image = flask.request.files['image']
    prompt = flask.request.form['instruction']

    # Parse image to pil image
    image = PIL.Image.open(image.stream).convert("RGB")
    prediction = alfred_pipeline({"image":image, "instruction":prompt})

    # Return the action
    return flask.jsonify({"action": prediction})

@app.route('/predict_rf', methods=['POST'])
def predict_rf():
    json = flask.request.get_json()

    # Parse the image from base64 to pil imag
    image = json['image']
    image = PIL.Image.open(io.BytesIO(base64.b64decode(image))).convert("RGB")
    
    # Parse the instruction history to a prompt
    instruction_history_d: list[dict] = json['instruction_history']
    instruction_history: list[PromptStep] = [PromptStep.from_dict(step) for step in instruction_history_d]
    print(instruction_history)
    
    t_init = time.time()
    prompt = AlfredExampleToInstruction(
                tokenizer, image.size
            ).build(instruction_history)
    elapsed_time = time.time() - t_init
    print(f"Time to build prompt: {elapsed_time}")
    
    print(prompt)
    # Get time that takes to predict
    t_init = time.time()
    prediction = alfred_pipeline({"image":image, "instruction":prompt})
    elapsed_time = time.time() - t_init
    print(f'Prediction: {prediction}')
    print(f"Time to predict: {elapsed_time}")

    # Return the action
    return flask.jsonify({"action": prediction})

# Run the app
if __name__ == "__main__":
    # Parse the config with argparse
    parser = HfArgumentParser((FlaskConfig, ModelConfig))
    flask_config, model_config = parser.parse_args_into_dataclasses()
    
    # Init
    model = AlfredUnimodelForConditionalGeneration.from_pretrained(model_config.model_name_or_path)
    tokenizer = AlfredTokenizer.from_pretrained(model_config.model_name_or_path)
    global alfred_pipeline
    alfred_pipeline = AlfredPipeline(model=model, tokenizer=tokenizer, device=1)

    # Run the app
    app.run(host=flask_config.host, port=flask_config.port)

