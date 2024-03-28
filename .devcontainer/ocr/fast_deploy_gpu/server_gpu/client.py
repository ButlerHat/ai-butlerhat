import time
import requests
import json
import cv2
import PIL.ImageDraw
import PIL.ImageFont
import PIL.Image
import fastdeploy as fd
from fastdeploy.serving.utils import cv2_to_base64

def print_ocr(example):
    img = example['image']
    # With pillow draw print in the image the text and the bbox
    draw = PIL.ImageDraw.Draw(img)
    for text, bbox in zip(example['text_list'], example['bbox_list']):
        draw.rectangle(bbox, outline='red')
        text = text.encode('utf-8').decode('utf-8')
        font = PIL.ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=12)

        draw.text((bbox[0], bbox[1]), text, font=font, fill='red')
    # Save image
    img.save(f"example_{example['instruction_history'][0]['name']}.png")

if __name__ == '__main__':
    url = "http://127.0.0.1:8000/fd/ppocrv3"
    headers = {"Content-Type": "application/json"}

    file_path = "/workspaces/ai-butlerhat/.devcontainer/ocr/fast_deploy_gpu/examples/telegram.png"
    im = cv2.imread(file_path)
    data = {"data": {"image": cv2_to_base64(im)}, "parameters": {}}

    t_start = time.time()
    resp = requests.post(url=url, headers=headers, data=json.dumps(data))
    t_end = time.time()
    print("Inference time: {}s".format(t_end - t_start))
    if resp.status_code == 200:
        r_json = json.loads(resp.json()["result"])
        print(r_json)
        ocr_result = fd.vision.utils.json_to_ocr(r_json)
        # vis_im = fd.vision.vis_ppocr(im, ocr_result)
        # cv2.imwrite("visualized_result.jpg", vis_im)
        img = PIL.Image.open(file_path)
        draw = PIL.ImageDraw.Draw(img)
        for text, bbox in zip(r_json['text'], r_json['boxes']):
            min_x = min(bbox[0], bbox[6])
            min_y = min(bbox[1], bbox[3])
            max_x = max(bbox[2], bbox[4])
            max_y = max(bbox[5], bbox[7])
            bbox_ = (min_x, min_y, max_x, max_y)
            draw.rectangle(bbox_, outline='red')
            text = text.encode('utf-8').decode('utf-8')
            font = PIL.ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=12)
            draw.text((bbox[0], bbox[1]), text, font=font, fill='red')
        # Save image
        
        save_path = "/workspaces/ai-butlerhat/.devcontainer/ocr/fast_deploy_gpu/examples/telegram2.png"
        img.save(save_path)

        print(f"Visualized result save in {save_path}")
    else:
        print("Error code:", resp.status_code)
        print(resp.text)
