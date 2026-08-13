import frappe
from candelabra.qr_service.generator import (
    generate_pay_by_square_qr, generate_generic_qr, image_to_base64,
)
from candelabra.qr_service.bysquare import build_pay_by_square

PBS_FRAME_PATH = frappe.get_app_path("candelabra", "public", "images", "pay_by_square_frame.png")

# fixne udaje, nemenia sa
IBAN = "SK4211000000002940290908"
BENEFICIARY_NAME = "Filip Degro"
CURRENCY = "EUR"


@frappe.whitelist()
def generate_payment_qr(amount: float, variable_symbol: str):
    cache_key = f"pbs_qr:{amount}:{variable_symbol}"
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return cached

    payload = build_pay_by_square(
        iban=IBAN,
        amount=float(amount),
        variable_symbol=variable_symbol,
        beneficiary_name=BENEFICIARY_NAME,
        currency=CURRENCY,
    )
    img = generate_pay_by_square_qr(payload, frame_path=PBS_FRAME_PATH)
    result = image_to_base64(img)
    frappe.cache().set_value(cache_key, result, expires_in_sec=3600)
    return result


@frappe.whitelist()
def generate_custom_qr(text: str, logo_attachment: str | None = None):
    logo_path = frappe.get_site_path(logo_attachment.lstrip("/")) if logo_attachment else None
    img = generate_generic_qr(text, logo_path=logo_path)
    return image_to_base64(img)