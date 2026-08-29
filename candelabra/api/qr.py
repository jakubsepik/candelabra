from candelabra.constants import BRAND_DIR,TYPE_MAP, QR_ICON_MAP, IBAN, BENEFICIARY_NAME, CURRENCY
import frappe
from candelabra.qr_service.generator import (
    generate_pay_by_square_qr, generate_generic_qr, image_to_base64,
)
from candelabra.qr_service.bysquare import build_pay_by_square
from frappe.utils.pdf import get_chrome_pdf

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


@frappe.whitelist()
def export_qr_pdf(doctype, names):
    names = frappe.parse_json(names)
    code_type = TYPE_MAP.get(doctype)
    if not code_type:
        frappe.throw(f"QR typ nie je nastavený pre {doctype}")

    pages = []
    for name in names:
        if code_type == "QRCODE":
            code = f"CDLB:{name}"
        else:
            code = f"CDLB:{code_type}:{name}"
        img_b64 = generate_custom_qr(code)
        label = f"{doctype}:{name}"
        pages.append(f"""
            <div class="qr-page">
                <div class="qr-frame">
                    <div class="qr-img-wrap">
                        <img src="data:image/png;base64,{img_b64}" />
                    </div>
                    <div class="qr-label">{label}</div>
                </div>
            </div>
        """)

    html = f"""
    <html>
    <head>
        <style>
            @page {{ size: 210mm 210mm; margin: 0; }}
            html, body {{ margin: 0; padding: 0; }}
            .qr-page {{
                page-break-after: always;
                width: 210mm;
                height: 210mm;
                display: flex;
                align-items: center;
                justify-content: center;
                box-sizing: border-box;
                padding: 10mm;
            }}
            .qr-frame {{
                position: relative;
                border: 3mm solid black;
                width: 100%;
                height: 100%;
                box-sizing: border-box;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 4mm;
            }}
            .qr-img-wrap {{
                width: 100%;
                height: 100%;
                display: flex;
                align-items: center;
                justify-content: center;
            }}
            .qr-img-wrap img {{
                width: 100%;
                height: 100%;
                object-fit: contain;
            }}
            .qr-label {{
                position: absolute;
                bottom: -6mm;
                left: 50%;
                transform: translateX(-50%);
                background: white;
                padding: 2mm 8mm;
                font-family: monospace;
                font-size: 20pt;
                white-space: nowrap;
            }}
        </style>
    </head>
    <body>{''.join(pages)}</body>
    </html>
    """

    pdf_bytes = get_chrome_pdf(
        print_format=None,
        html=html,
        options={},
        output=None,
        pdf_generator="chrome",
    )

    if not pdf_bytes:
        frappe.throw("PDF generovanie zlyhalo")

    frappe.local.response.filename = f"{doctype}_qr_codes.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "download"