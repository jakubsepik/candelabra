import frappe

TYPE_MAP = {
    "QR Code Link": "QRCODE",
    "Item": "ITEM",
}

TYPE_MAP_REVERSE = {v: k for k, v in TYPE_MAP.items()}

BRAND_DIR = frappe.get_app_path("candelabra", "public", "brand")

QR_ICON_MAP = {
    "Customer": "customer.png",
    "Sales Invoice": "sales_invoice.png",
    "Item": "item.png",
    "Employee": "employee.png",
}

IBAN = "SK4211000000002940290908"
BENEFICIARY_NAME = "Filip Degro"
CURRENCY = "EUR"

def set_bootinfo(bootinfo):
    bootinfo.candelabra_type_map = TYPE_MAP
    bootinfo.candelabra_type_map_reverse = TYPE_MAP_REVERSE
    bootinfo.candelabra_brand_dir = BRAND_DIR
    bootinfo.candelabra_qr_icon_map = QR_ICON_MAP
    bootinfo.candelabra_iban = IBAN
    bootinfo.candelabra_beneficiary_name = BENEFICIARY_NAME
    bootinfo.candelabra_currency = CURRENCY