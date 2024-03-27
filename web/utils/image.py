from buibert.action_and_state import ModelObservation


def convert_rgba_to_rgb(str_screenshot: str) -> str:
        """
        Convert a screenshot from RGBA to RGB.

        :param str_screenshot: The screenshot in RGBA format.
        """
        pil_img = ModelObservation._decode_base64(str_screenshot)
        rgb_img = pil_img.convert('RGB')
        return ModelObservation._encode_base64(rgb_img)