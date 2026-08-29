import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M
from qrcode.image.styledpil import StyledPilImage
from PIL import Image
import io
import base64
import os


def _build_base(data: str, error_correction=ERROR_CORRECT_M, box_size: int = 10,
                 fill_color: str = "black", back_color: str = "white") -> Image.Image:
    qr = qrcode.QRCode(error_correction=error_correction, box_size=box_size, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGBA") # type: ignore


def generate_generic_qr(text: str, logo_path: str | None = None, box_size: int = 10) -> Image.Image:
    if not logo_path:
        return _build_base(text, error_correction=ERROR_CORRECT_M, box_size=box_size)

    logo_image = _flatten_logo_to_white(logo_path)

    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, box_size=box_size, border=4)
    qr.add_data(text)
    qr.make(fit=True)

    img = qr.make_image(
        image_factory=StyledPilImage,
        embedded_image=logo_image,
        embedded_image_ratio=0.22,
    )
    return img.convert("RGBA")


def _flatten_logo_to_white(logo_path: str) -> Image.Image:
    """
    Otvori logo a ak ma transparentnost, skomponuje ho na biele pozadie.
    Vrati PIL Image objekt (v pamati, ziadny docasny subor).
    """
    img = Image.open(logo_path)

    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        img = img.convert("RGBA")
        background = Image.new("RGBA", img.size, (255, 255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        return background.convert("RGB")

    return img.convert("RGB")

PBS_FRAME_BOX = (6, 7, 452, 454)  # left, top, right, bottom - qr placement area, 462x541 asset


def generate_pay_by_square_qr(payload: str, frame_path: str) -> Image.Image:
    """
    QR sa vklada dovnutra ramu, wordmark 'PAY by square' je uz sucastou assetu.
    """
    img = _build_base(payload, error_correction=ERROR_CORRECT_M, box_size=10)
    return _compose_with_frame(img, frame_path)


def _compose_with_frame(qr_img: Image.Image, frame_path: str) -> Image.Image:
    frame = Image.open(frame_path).convert("RGBA")
    left, top, right, bottom = PBS_FRAME_BOX
    box_w, box_h = right - left, bottom - top

    qr_resized = qr_img.convert("RGBA").resize((box_w, box_h))
    canvas = frame.copy()
    canvas.paste(qr_resized, (left, top))
    return canvas


def image_to_base64(img: Image.Image, fmt: str = "PNG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode()