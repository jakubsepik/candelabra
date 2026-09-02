from candelabra.constants import BRAND_DIR, QR_ICON_MAP, IBAN, BENEFICIARY_NAME, CURRENCY
import frappe
from candelabra.qr_service.generator import (
    generate_pay_by_square_qr, generate_generic_qr, image_to_base64,
)
from candelabra.qr_service.bysquare import build_pay_by_square


PBS_FRAME_PATH = f"{BRAND_DIR}/pay_by_square_frame.png"

@frappe.whitelist()
def generate_payment_qr(amount: float, variable_symbol: str):
    cache_key = f"pbs_qr:{amount}:{variable_symbol}"
    cached = frappe.cache().get_value(cache_key) # type: ignore
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
    frappe.cache().set_value(cache_key, result, expires_in_sec=3600) # type: ignore
    return result


def _resolve_icon_path(doctype: str | None) -> str:
    COMPANY_LOGO_PATH = f"{BRAND_DIR}/logo_mono.png"
    if doctype is None:
        return COMPANY_LOGO_PATH
    filename = QR_ICON_MAP.get(doctype)
    return f"{BRAND_DIR}/{filename}" if filename else COMPANY_LOGO_PATH


@frappe.whitelist()
def generate_custom_qr(text: str, doctype: str | None = None):
    cache_key = f"custom_qr:{text}:{doctype or 'company'}"
    cached = frappe.cache().get_value(cache_key) # type: ignore
    if cached:
        return cached

    logo_path = _resolve_icon_path(doctype)
    img = generate_generic_qr(text, logo_path=logo_path)
    result = image_to_base64(img)
    frappe.cache().set_value(cache_key, result, expires_in_sec=3600) # type: ignore
    return result

