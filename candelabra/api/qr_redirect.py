import frappe
from urllib.parse import quote


@frappe.whitelist(allow_guest=True)
def redirect(id: str | None = None):
    if not id:
        frappe.throw("Chýba ID QR odkazu")

    qr_link = frappe.db.get_value(
        "QR Code Link",
        id,
        ["reference_doctype", "reference_name"],
        as_dict=True,
    )

    if qr_link is None:
        frappe.throw("QR odkaz neexistuje")

    reference_doctype = qr_link.get("reference_doctype")
    reference_name = qr_link.get("reference_name")

    if not reference_doctype or not reference_name:
        frappe.throw("QR odkaz nemá platný cieľ")

    target_url = (
        f"/app/{frappe.scrub(reference_doctype)}"
        f"/{quote(reference_name, safe='')}"
    )

    frappe.local.response.type = "redirect"
    frappe.local.response.location = target_url