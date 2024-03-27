import io
import base64
import numpy as np
from PIL import Image
from typing import List, Union
from io import BytesIO
from buibert.action_and_state import Word
import streamlit as st
import requests


class OCR:
    def __init__(self, lang: str):
        self.lang = lang

    def image_to_text(self, image: str):
        raise NotImplementedError

    @staticmethod
    def create_word_with_bbox(text, x, y, w, h):
        # Word(_['s'], _['x'] + 0.5*_['w'], _['y']+0.5*_['h'], _['w'], _['h'])
        return Word(text, x + 0.5 * w, y + 0.5 * h, w, h)

    @staticmethod
    def encode_base64_to_numpy(image_str: str) -> np.ndarray:
        image = Image.open(io.BytesIO(base64.b64decode(image_str)))
        return np.array(image)[...,:3]

    @staticmethod
    def encode_base64_to_pillow(image_str: str) -> Image.Image:
        return Image.open(io.BytesIO(base64.b64decode(image_str)))

class OCRPaddle(OCR):
    def __init__(self, lang='en'):
        from paddleocr import PaddleOCR  # type: ignore
        super().__init__(lang)
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang)

    def image_to_text(self, image: Union[str, np.ndarray]) -> List[Word]:
        result = self.ocr.ocr(image, cls=True)

        # Create words
        words = []
        for res in result:
            for line in res:
                if line[1][1] > 0.8:
                    text = line[1][0]
                    x = line[0][0][0]
                    y = line[0][0][1]
                    w = line[0][2][0] - x
                    h = line[0][2][1] - y
                    words.append(OCR.create_word_with_bbox(text, x, y, w, h))
        return words


class OCRPaddleApi(OCR):
    def __init__(self, lang='en'):
        super().__init__(lang)
        self.url = st.secrets.urls.ocr

    def image_to_text(self, image: Union[str, Image.Image], format: str ='PNG') -> List[Word]:
        if isinstance(image, str):
            image = OCR.encode_base64_to_pillow(image)

        # Transform image to send in request
        byte_io = BytesIO()
        image.save(byte_io, format=format)
        byte_io.seek(0)
        response = requests.post(f"{self.url}/ocr", files={"image": byte_io}, data={"lang": "en"})  # type: ignore
        result = response.json()["result"]

        # Create words
        words = []
        for res in result:
            for line in res:
                if line[1][1] > 0.8:
                    text = line[1][0]
                    x = line[0][0][0]
                    y = line[0][0][1]
                    w = line[0][2][0] - x
                    h = line[0][2][1] - y
                    words.append(OCR.create_word_with_bbox(text, x, y, w, h))
        return words