import frappe
from frappe.model.document import Document


class QRCodeLink(Document):
    def autoname(self):
        for _ in range(5):
            name = frappe.generate_hash(length=6)
            if not frappe.db.exists("QR Code Link", name):
                self.name = name
                return
        frappe.throw("Nepodarilo sa vygenerovať unikátne QR ID")