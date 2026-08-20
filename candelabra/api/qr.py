import frappe
from candelabra.qr_service.generator import (
    generate_pay_by_square_qr, generate_generic_qr, image_to_base64,
)
from candelabra.qr_service.bysquare import build_pay_by_square

PBS_FRAME_PATH = frappe.get_app_path("candelabra", "public", "qr_images", "pay_by_square_frame.png")

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


QR_ICONS_DIR = frappe.get_app_path("candelabra", "public", "qr_images")
COMPANY_LOGO_PATH = f"{QR_ICONS_DIR}/logo.png"

QR_ICON_MAP = {
    "Customer": "customer.png",
    "Sales Invoice": "sales_invoice.png",
    "Item": "item.png",
    "Employee": "employee.png",
}


def _resolve_icon_path(doctype: str | None) -> str:
    if doctype is None:
        return COMPANY_LOGO_PATH
    filename = QR_ICON_MAP.get(doctype)
    return f"{QR_ICONS_DIR}/{filename}" if filename else COMPANY_LOGO_PATH


@frappe.whitelist()
def generate_custom_qr(text: str, doctype: str | None = None):
    cache_key = f"custom_qr:{text}:{doctype or 'company'}"
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return cached

    logo_path = _resolve_icon_path(doctype)
    img = generate_generic_qr(text, logo_path=logo_path)
    result = image_to_base64(img)
    frappe.cache().set_value(cache_key, result, expires_in_sec=3600)
    return result


from candelabra.constants import TYPE_MAP

@frappe.whitelist()
def export_qr_codes(doctype, names):
    names = frappe.parse_json(names)

    code_type = TYPE_MAP.get(doctype)
    if not code_type:
        frappe.throw(f"QR typ nie je nastavený pre {doctype}")

    if code_type == "QRCODE":
        lines = [f"CDLB:{name}" for name in names]
    else:
        lines = [f"CDLB:{code_type}:{name}" for name in names]
    return "\n".join(lines)