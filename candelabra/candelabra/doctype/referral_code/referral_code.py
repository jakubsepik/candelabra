# Copyright (c) 2026, Jakub Šepeľa and contributors
# For license information, please see license.txt

import frappe
import secrets
import string
from frappe.model.document import Document


class ReferralCode(Document):
	def validate(self):
		if self.referral_code:
			return
		alphabet = string.ascii_uppercase + string.digits
		while True:
			code = "".join(secrets.choice(alphabet) for _ in range(8))
			if not frappe.db.exists("Custom Referral Code", {"referral_code": code}):
				self.referral_code = code
				break
