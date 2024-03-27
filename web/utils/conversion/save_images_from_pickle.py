import pickle
import sys
import os
import base64
from PIL import Image
from io import BytesIO

from ButlerRobot.src.data_types import Task


# input_pickle_path = '/workspaces/BUIBert/robotframework/data/data_interpreter/Test.pickle'
input_pickle_path = '/workspaces/BUIBert/robotframework/Web/frontend/data/edit/full_home_amazon.pickle'

# output_path = '/workspaces/BUIBert/robotframework/data/data_interpreter'
output_path = '/workspaces/BUIBert/robotframework/Web/frontend/utils/borrar'


def encode_image(image_str):
    # Encode base64 string to bytes
    image_bytes = image_str.encode('ascii')

    # Decode bytes to image
    image = Image.open(BytesIO(base64.b64decode(image_bytes)))
    return image


with open(input_pickle_path, 'rb') as f:
    task: Task = pickle.load(f)

# Iterate through each task.step and save image
for i, step in enumerate(task.steps):
    start_observation:str = step.context.start_observation.screenshot
    end_observation:str = step.context.end_observation.screenshot

    # Decode bytes to image
    start_observation_image = encode_image(start_observation)
    end_observation_image = encode_image(end_observation)

    start_path = f'{output_path}{os.sep}{i}_1-start_{step.name}.png'
    end_path = f'{output_path}{os.sep}{i}_2-end_{step.name}.png'

    start_observation_image.save(start_path)
    end_observation_image.save(end_path)

# Save start and end task images
start_task_observation = task.context.start_observation.screenshot
end_task_observation = task.context.end_observation.screenshot

# Decode bytes to image
start_task_observation_image = encode_image(start_task_observation)
end_task_observation_image = encode_image(end_task_observation)

start_task_observation_image.save(f'{output_path}{os.sep}start_task_{task.name}.png')
end_task_observation_image.save(f'{output_path}{os.sep}end_task_{task.name}.png')

