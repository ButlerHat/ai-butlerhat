import os
import io
import json
import base64
from typing import Optional, Union
from collections import namedtuple
import requests
import torch
import torchvision.transforms as T
import fastdeploy as fd
import PIL.Image
import PIL.ImageDraw
import PIL.ImageFont
import datasets
from torchvision.transforms import functional as F
from datasets import load_dataset  # type: ignore
# import sys
# sys.path.append('/workspaces/ai-butlerhat')
from core.models import AlfredTokenizer
from ButlerRobot.src.data_to_ai.data_types import PromptStep


def get_visual_bbox(image_size=224):
    image_feature_pool_shape = [image_size//16, image_size//16]
    # Disable E1101:no-member
    visual_bbox_x = (torch.arange(  # pylint: disable=no-member
        0,
        1.0 * (image_feature_pool_shape[1] + 1),
        1.0,
    ) / image_feature_pool_shape[1])
    visual_bbox_y = (torch.arange(  # pylint: disable=no-member
        0,
        1.0 * (image_feature_pool_shape[0] + 1),
        1.0,
    ) / image_feature_pool_shape[0])
    visual_bbox_input = torch.stack(  # pylint: disable=no-member
        [
            visual_bbox_x[:-1].repeat(
                image_feature_pool_shape[0], 1),
            visual_bbox_y[:-1].repeat(
                image_feature_pool_shape[1], 1).transpose(
                    0, 1),
            visual_bbox_x[1:].repeat(
                image_feature_pool_shape[0], 1),
            visual_bbox_y[1:].repeat(
                image_feature_pool_shape[1], 1).transpose(
                    0, 1),
        ],
        dim=-1,
    ).view(-1, 4)
    return visual_bbox_input

def normalText(t):
    if type(t) is float:
        if t == int(t):
            t = int(t)
    t = str(t)
    return t.strip()

def request_ocr(url: str, image: PIL.Image.Image, lang='en', format='PNG'):
    # Transform image to base64 string
    byte_io = io.BytesIO()
    image.save(byte_io, format=format)
    byte_io = byte_io.getvalue()
    img_str = base64.b64encode(byte_io).decode('utf-8')
    
    headers = {"Content-Type": "application/json"}
    data = {"data": {"image": img_str}, "parameters": {}}
    response = requests.post(url=url, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        r_json = json.loads(response.json()["result"])
        return fd.vision.utils.json_to_ocr(r_json)
    else:
        raise Exception(f"Error in ocr request. Code: {response.status_code} Text: {response.text}")

def process_ocr(url, image: PIL.Image.Image, tokenizer, lang='en') -> Optional[tuple]:
    """
    Process TiffImageFile with OCR, tokenize the text and for every token create a bounding box.
    :param image: Image. Image to process.
    :param tokenizer: Tokenizer. Tokenizer to use.
    :param image_size: int. Size of the image.
    :return: tuple. list_tokens, list_bboxes, image, page_size
    """
    text_list, bbox_list = [], []
    page_size = image.size

    try:
        result = request_ocr(url, image, lang)
    except Exception as e:
        print(f"OCR failed for {url}: {e}")
        return None
    
    for box, text in zip(result.boxes, result.text):
    # box = [top_left-x, top_left-y, top_right-x, top_right-y, bottom_right-x, bottom_right-y, bottom_left-x, bottom_left-y]
        text = normalText(text)
        if text == '':
            continue
        sub_tokens = tokenizer.tokenize(text)
        min_x = min(box[0], box[6])
        min_y = min(box[1], box[3])
        max_x = max(box[2], box[4])
        max_y = max(box[5], box[7])
        for sub_token in sub_tokens:
            text_list.append(sub_token)
            bbox_list.append([min_x, min_y, max_x, max_y])

    assert len(text_list) == len(bbox_list)

    return text_list, bbox_list, page_size


class Normalize(object):
    def __init__(self, mean, std, format='rgb'):
        self.mean = mean
        self.std = std
        self.format = format.lower()

    def __call__(self, image):
        if 'bgr' in self.format:
            image = image[[2, 1, 0]]
        if '255' in self.format:
            image = image * 255
        if image.size(0) == 1:
            image = image.repeat(3, 1, 1)
        image = F.normalize(image, mean=self.mean, std=self.std)
        return image

def img_trans_torchvision(image, image_size=224):
    trans = T.Compose([
            T.Resize([image_size,image_size]),
            T.ToTensor(),
            Normalize(
            mean=[0.485, 0.456, 0.406],
            std=[0.229, 0.224, 0.225]
        )])

    image = trans(image)  # copy to make it writeable
    return image


class AlfredExampleToInstruction:
    def __init__(self, tokenizer: AlfredTokenizer, page_size: tuple):
        self.tokenizer: AlfredTokenizer = tokenizer
        self.page_size = page_size

    def action_to_string(self, action: PromptStep) -> str:
        """
        Action is a dict with keys: name, args, type
        Result: action_name string bbox.
        Example: Input text "Hello" <loc_50><loc_100><loc_250><loc_300>
        """
        prompt = ""
        s = f' "{action.args["string"]}" ' if 'string' in action.args and action.args['string'] else ''
        bbox: Union[dict, str] = action.args['bbox'] if action.args.get('bbox', '') else ''
        if isinstance(bbox, dict):
            x, y, w, h = bbox['x'], bbox['y'], bbox['width'], bbox['height']
            tokens_bbox = self.tokenizer.convert_bbox_to_token([x, y, x+w, y+h], self.page_size)
            bbox = "".join([str(t) for t in tokens_bbox])
        prompt += action.name + s + bbox
        return prompt
        
    def build(self, instruction_history:'list[PromptStep]'):
        prompt = "Instruction: "
        for instruction in instruction_history:
            if instruction.type == 'task':
                prompt += "task: " + instruction.name + " > "
            elif instruction.type == 'action':
                prompt += "action: " + self.action_to_string(instruction) + " > "
        prompt = prompt[:-3]
        return prompt


class HfRobotframeworkDatasetBuilder:

    def __init__(
            self, 
            data_args, 
            tokenizer, 
            num_proc=12, 
            ocr_url: str = "http://nginx_alfred:80/fd/ppocrv3",
            print_func=print
        ):
        file_dir = "/workspaces/ai-butlerhat/core/datasets"
        cache_dir = os.sep.join(file_dir.split(os.sep)[:-2]) + os.sep + '.hf_cache'
        
        self.ocr_url = ocr_url
        self.tokenizer: AlfredTokenizer = tokenizer
        self.max_seq_length = data_args.max_seq_length
        self.image_size = data_args.image_size
        dataset_dir = data_args.dataset_dir
        dataset_valid_dir = data_args.dataset_valid_dir
        validation_split = data_args.validation_split
        self.num_proc = num_proc
        self.print_func = print_func
        
        # Load dataset
        dataset: datasets.DatasetDict = load_dataset("json", data_dir=dataset_dir, cache_dir=cache_dir) # type: ignore
        dataset_valid = None
        if dataset_valid_dir:
            dataset_valid: Optional[datasets.DatasetDict] = load_dataset("json", data_dir=dataset_valid_dir, cache_dir=cache_dir)  # type: ignore
        assert isinstance(dataset, datasets.DatasetDict)

        # Clean dataset before splitting
        filter_not = lambda example: all([instruction['name'].lower() != 'not' for instruction in example['instruction_history']])
        # Copy dataset
        dataset = dataset.filter(filter_not)
        
        # Split dataset
        if validation_split > 0:
            assert validation_split < 1, "Validation split must be between 0 and 1"
            train_dataset = dataset['train'].train_test_split(test_size=0.1, seed=44)
            # val_dataset = train_dataset['train'].train_test_split(test_size=0.1, seed=42)
            self.dataset = datasets.DatasetDict({
                'train': train_dataset['train'],
                'validation': train_dataset['test'],
                # 'test': train_dataset['test']
            })
        else:
            self.dataset = datasets.DatasetDict({
                'train': dataset['train'],
                'validation': dataset['train']
                # 'test': train_dataset['test']
            })
        
        # Override validation dataset if provided
        if dataset_valid:
            self.dataset['validation'] = dataset_valid['train']

        # Print size of dataset
        self.print_func(f"Train size: {len(self.dataset['train'])}")
        self.print_func(f"Validation size: {len(self.dataset['validation'])}")
        # print(f"Test size: {len(self.dataset['test'])}")

    def build_dataset(self):
        self.print_func("Building dataset")
        dataset = self.dataset

        self.print_func("Convert images...")
        # Convert str
        img_convert = lambda example: {
            "image": PIL.Image.open(io.BytesIO(base64.b64decode(example['screenshot']))).convert('RGB')
        }
        dataset = dataset.map(img_convert, num_proc=self.num_proc, remove_columns=['screenshot'])

        self.print_func("Processing OCR...")
        def read_image(example):
            result = process_ocr(self.ocr_url, example['image'], self.tokenizer)
            if result is None:
                return {
                "text_list": None,
                "bbox_list": None,
                "page_size": None
            }
            text_list, bbox_list, page_size = result
            return {
                "text_list": text_list,
                "bbox_list": bbox_list,
                "page_size": page_size
            }
        dataset = dataset.map(read_image, num_proc=self.num_proc)

        # Show 3 examples
        # data_to_print = dataset['train'].shuffle(seed=42).select(range(3))
        # def print_ocr(example):
        #     img = example['image']
        #     # With pillow draw print in the image the text and the bbox
        #     draw = PIL.ImageDraw.Draw(img)
        #     for text, bbox in zip(example['text_list'], example['bbox_list']):
        #         draw.rectangle(bbox, outline='red')
        #         text = text.encode('utf-8').decode('utf-8')
        #         font = PIL.ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size=12)

        #         draw.text((bbox[0], bbox[1]), text, font=font, fill='red')
        #     # Save image
        #     img.save(f"example_{example['instruction_history'][0]['name']}.png")
        # data_to_print.map(print_ocr)

        self.print_func("Filtering out None images and labels...")
        self.print_func(f'Number of examples before: {len(dataset["train"])}')
        filter_nones = lambda example: all(example[key] is not None for key in ['image', 'text_list', 'bbox_list', 'page_size'])
        dataset = dataset.filter(filter_nones)
        self.print_func(f'Number of examples after: {len(dataset["train"])}')
        print(dataset['train'][0].keys())
        
        self.print_func("Processing images...")
        process_image = lambda example: {
            "image": img_trans_torchvision(example['image'], self.image_size)
        }
        dataset = dataset.map(process_image, num_proc=self.num_proc)
        print(dataset['train'][0].keys())

        self.print_func("Normalizing bounding boxes...")
        def normalize_bboxes(example):
            new_bboxes = []
            width, height = example['page_size']
            for bbox in example['bbox_list']:
                new_bbox = [bbox[0] / width, bbox[1] / height, bbox[2] / width, bbox[3] / height]
                new_bboxes.append(new_bbox)
            return {
                "bbox_list": new_bboxes,
            }
        dataset = dataset.map(normalize_bboxes)
        print(dataset['train'][0].keys())
        
        self.print_func("Adding visual bounding boxes...")
        add_visual_bboxes = lambda _: {"visual_seg_data": get_visual_bbox(self.image_size)}
        dataset = dataset.map(add_visual_bboxes)
        print(dataset['train'][0].keys())
        
        self.print_func("Convert tokens to ids...")
        tokens_to_ids = lambda example: {
                "token_list": self.tokenizer.convert_tokens_to_ids(example['text_list']),
            }
        dataset = dataset.map(tokens_to_ids)
        print(dataset['train'][0].keys())
        
        self.print_func("Making prompt...")
        def make_prompt(example):
            # Instruction history is the input, step=PageAction is the label. Could be task or action.
            prompt_text = "Web action and object layout prediction."
            list_steps = [PromptStep.from_dict(step) for step in example['instruction_history']]
            instruction = AlfredExampleToInstruction(
                self.tokenizer, example['page_size']
            ).build(list_steps)
            # Change from step to action. This line is for support legacy code
            key_action = 'action' if 'action' in example else 'step'
            gt_step = PromptStep.from_dict(example[key_action])
            label = AlfredExampleToInstruction(
                self.tokenizer, example['page_size']
            ).action_to_string(gt_step)
            label = example[key_action]['type'] + ": " + label

            return {
                "prompt": prompt_text,
                "instruction": instruction,
                "label": label,
                # This line is for support legacy code. Add the action type to remove in the future
                "action": "",
                "step": ""
            }
        dataset = dataset.map(make_prompt)

        self.print_func("Convert to seq2seq...")
        def convert_seq_to_seq(example):
            # Encoder
            prompt = example['prompt'] + " " + example['instruction']
            prompt_ids =  self.tokenizer.encode(prompt, add_special_tokens=False)
            input_ids = prompt_ids + example['token_list']  # To add prompt to input ids
            input_ids = input_ids[:self.max_seq_length]  # To truncate
            bbox_list = [[0,0,0,0]] * len(prompt_ids) + example['bbox_list']  # To add prompt with empty bbox
            # Decoder
            seq_labels = self.tokenizer(example['label'], add_special_tokens=True) # To add EOS token
            
            attention_mask = [1] * len(input_ids)
            
            return {
                "input_ids": input_ids,
                "bbox_list": bbox_list,
                "seq_labels": seq_labels['input_ids'],
                "attention_mask": attention_mask,
                "decoder_attention_mask": seq_labels['attention_mask'],
            }
        dataset = dataset.map(convert_seq_to_seq, num_proc=self.num_proc)
        print(dataset['train'][0].keys())

        add_char = lambda _: {"char_ids": [0]}
        dataset = dataset.map(add_char, num_proc=self.num_proc)
        add_char_seg_data = lambda _: {"char_seg_data": [[0,0,0,0]]}
        dataset = dataset.map(add_char_seg_data, num_proc=self.num_proc)

        self.print_func("Shaping data...")
        def shape_data(example):
            return {
                "input_ids": example['input_ids'],
                "attention_mask": example['attention_mask'],
                "labels": example['seq_labels'],
                "seg_data": example['bbox_list'],
                "visual_seg_data": example['visual_seg_data'],
                "decoder_attention_mask": example['decoder_attention_mask'],
                "image": example['image'],
                "char_ids": example['char_ids'],
                "char_seg_data": example['char_seg_data']
            }
        dataset = dataset.map(shape_data, num_proc=self.num_proc, remove_columns=dataset["train"].column_names)
        dataset.set_format(type='torch')
        print(dataset['train'][0].keys())

        self.print_func("Final check...")
        self.print_func(f'Number of examples before: {len(dataset["train"])}')
        final_check = lambda example: all([
            len(example['input_ids']) == len(example['seg_data']),
            len(example['seg_data'].size()) == 2,
            len(example['char_seg_data'].size()) == 2
        ])
        dataset.filter(final_check)
        self.print_func(f'Number of examples after: {len(dataset["train"])}')

        return dataset

# Main
if __name__ == '__main__':

    tokenizer = AlfredTokenizer.from_pretrained(
        "/workspaces/ai-butlerhat/model/hf",
        cache_dir="/workspaces/ai-butlerhat/.hf_cache/transformers",
        use_fast=True
    )

    DataArgs = namedtuple('DataArgs', ['dataset_dir', 'max_samples', 'max_seq_length', 'image_size', 'validation_split', 'dataset_valid_dir'])
    dataset_dir = "/workspaces/ai-butlerhat/ai-butlerhat-projects/default/rpa_dataset"
    output_dir = "/workspaces/ai-butlerhat/ai-butlerhat-projects/default/pretraining_dataset"
    # Valid dataset is to train with all samples to train (validation_split=0) and then use the valid dataset random to evaluate
    valid_dir = ""  # Uncomment to not use valid dataset
    # valid_dir = "/workspaces/ai-butlerhat/data-butlerhat/robotframework-butlerhat/TestSuites/CicloZero/data/validation"
    data_args = DataArgs(dataset_dir=dataset_dir, max_samples=-1, max_seq_length=512, image_size=224, validation_split=0.1, dataset_valid_dir=valid_dir)
    new_dataset = HfRobotframeworkDatasetBuilder(data_args, tokenizer, num_proc=20).build_dataset()  # Implementing this function in streamlit with num_proc>1 fails, I think is a bug of not running in main
    new_dataset.save_to_disk(output_dir)
