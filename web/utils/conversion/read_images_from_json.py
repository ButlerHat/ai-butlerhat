import json
import PIL.Image
import PIL.ImageDraw
import base64
import io
import os

# Read images from json file
json_file = '/workspaces/BUIBert/bertbui/static/pta_bbox/valid/pta/999.json'
save_dir = '/workspaces/BUIBert/robotframework/Web/frontend/utils/borrar/from_json'
# Create save directory if it does not exist
if not os.path.exists(save_dir):
    os.makedirs(save_dir)


with open(json_file) as f:
    data = json.load(f)

# Save images
def render_images(data):
    for i, observation in enumerate(data['observations']):
        img = PIL.Image.open(io.BytesIO(base64.b64decode(observation['screenshot'])))
        draw = PIL.ImageDraw.Draw(img)
        # Print bbox
        last_action = observation['last_action']
        if last_action['element_wh'] != (1, 1):
            w = last_action['element_wh'][0]
            h = last_action['element_wh'][1]
            x = last_action['pointer_xy'][0] - w / 2
            y = last_action['pointer_xy'][1] - h / 2
            draw.rectangle([x, y, x + w, y + h], outline='red', width=2)
        # Print detected words
        for word in observation['detected_words']:
            w = word['surface']
            cx = word['cx']
            cy = word['cy']
            width = word['width']
            height = word['height']
            draw.rectangle([cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2], outline='blue', width=2)
            # Drow text on top of the rectangle
            draw.text((cx - width / 2, cy - (height + 5)), w, fill='blue')

        img.save(save_dir + f'/image{i}.png')

render_images(data)

