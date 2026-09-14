# candelabra/candelabra/api/revenue.py
#
# Backend pre revenue-graph page. Kazda funkcia vracia {"roots": [...], "trunk": {...}, "crown": [...]}
# vo formate, ktory ocakava revenue_graph.js (label, amount, volitelne type a link).
#
# Company scope pouziva Project.gross_margin (total_billed_amount - total_costing_amount),
# co je pole, ktore ERPNext sam prepocitava pri ulozeni Project dokumentu (update_costing).
# Ak gross_margin nie je nikdy prepocitany (0 pre vsetky), treba spustit
# bench execute frappe.client.bulk_update alebo project.update_costing() rucne / cez scheduled job.

import frappe
from frappe import _

SCOPE_TYPES = ("company", "project", "employee")


@frappe.whitelist()
def get_revenue_graph_data(scope_type="company", scope_name=None):
    scope_type = (scope_type or "company").lower()
    if scope_type not in SCOPE_TYPES:
        frappe.throw(_("Invalid scope_type"))

    check_scope_permission(scope_type, scope_name)

    if scope_type == "company":
        return get_company_scope()
    if scope_type == "project":
        return get_project_scope(scope_name)
    if scope_type == "employee":
        return get_employee_scope(scope_name)


def check_scope_permission(scope_type, scope_name):
    if "System Manager" in frappe.get_roles() or "Accounts Manager" in frappe.get_roles():
        return

    if scope_type == "employee":
        user_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not user_employee or user_employee != scope_name:
            frappe.throw(_("Not permitted"), frappe.PermissionError)
        return

    frappe.throw(_("Not permitted"), frappe.PermissionError)


# ----------------------------------------------------------------------
# COMPANY SCOPE - roots = projekty a ich zisk (gross_margin), crown = TODO
# ----------------------------------------------------------------------
def get_company_scope():
    company = frappe.defaults.get_user_default("company") or frappe.defaults.get_global_default("company")
    print(f"get_company_scope: company={company}")
    projects = frappe.get_all(
        "Project",
        filters={
            "status": ["not in", ["Cancelled"]],
            "company": company,
        },
        fields=["name", "project_name", "gross_margin", "total_billed_amount", "total_costing_amount"],
    )
    print(f"get_company_scope: found {len(projects)} projects for company {company}")
    roots = []
    for p in projects:

        amount = p.gross_margin

        if not amount or amount <= 0:
            continue

        roots.append({
            "label": p.project_name or p.name,
            "amount": amount,
            "link": {"scope_type": "project", "scope_name": p.name},
        })

    trunk = {
        "label": "Celkovy zisk",
        "amount": sum(r["amount"] for r in roots),
    }

    # TODO: crown - distribucne ciele (zamestnanci/material/admin/...) z Journal Entry
    crown = []

    return {"roots": roots, "trunk": trunk, "crown": crown}


# ----------------------------------------------------------------------
# PROJECT SCOPE - roots = faktury projektu, trunk = zisk projektu (gross_margin)
# ----------------------------------------------------------------------
def get_project_scope(project):
    if not project:
        frappe.throw(_("scope_name (project) required"))

    proj = frappe.db.get_value(
        "Project", project,
        ["project_name", "gross_margin", "total_billed_amount", "total_costing_amount"],
        as_dict=True,
    )
    if not proj:
        frappe.throw(_("Project not found"))

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"project": project, "docstatus": 1},
        fields=["name", "grand_total"],
    )

    roots = [
        {"label": inv.name, "amount": inv.grand_total}
        for inv in invoices
        if inv.grand_total
    ]

    amount = proj.gross_margin
    if not amount and proj.total_billed_amount:
        amount = (proj.total_billed_amount or 0) - (proj.total_costing_amount or 0)

    trunk = {"label": proj.project_name or project, "amount": amount or 0}

    # TODO: crown - rozdelenie zisku projektu (zamestnanci podla Timesheet hours + naklady)
    crown = []

    return {"roots": roots, "trunk": trunk, "crown": crown}


# ----------------------------------------------------------------------
# EMPLOYEE SCOPE - zatial TODO, staticky prazdny vysledok
# ----------------------------------------------------------------------
def get_employee_scope(employee):
    if not employee:
        frappe.throw(_("scope_name (employee) required"))

    # TODO: roots = projekty z Timesheet, kde employee zapisal hodiny
    # TODO: trunk = sucet vyplateneho podielu employee (Journal Entry)
    return {"roots": [], "trunk": {"label": employee, "amount": 0}, "crown": []}

# Schéma dát pre graf príjmov:
# roots = hlavné uzly (napr. projekty / zákazky) s hodnotou príjmu
# trunk = celkový súhrn pre aktuálny rozsah (label + celková suma)
# crown = rozdelenie príjmu na kategórie (zamestnanci, materiál, admin, IT, fakturácia, referral)
REVENUE_GRAPH_SCHEMA = {
    "roots": [
        {
            "label": "string, max 18 znakov zobrazenych (dlhsie sa orezu)",
            "amount": "number, EUR, > 0",
        }
    ],
    # Jeden hlavný súhrnný uzol pre aktuálny scope (napr. spoločnosť / projekt / zamestnanec)
    "trunk": {"label": "string", "amount": "number, EUR"},
    "crown": [
        {
            # Typ rozdelenia príjmu do jednotlivých kategórií
            "type": "employee | material | admin | it | invoicing | referral",
            "label": "string, max 18 znakov zobrazenych",
            "amount": "number, EUR, > 0",
        }
    ],
}