# candelabra/candelabra/api/revenue.py
#
# Backend pre revenue-graph page. Kazda funkcia vracia {"roots": [...], "trunk": {...}, "crown": [...]}
# vo formate, ktory ocakava revenue_graph.js (label, amount, type, volitelne link).
#
# KAZDY node (root aj crown) ma teraz povinne pole "type", podla ktoreho frontend
# vyfarbuje bodku a link v legende. Existujuce typy (pouzite v crown, distribucne
# ciele): employee, material, admin, it, invoicing, referral.
# Nove typy (pouzite v roots, zdroje prijmu): project, invoice.
# Ak pridas dalsi typ, treba ho doplnit aj do dot_color / legendy vo frontende.
#
# Company scope pouziva Project.gross_margin (total_billed_amount - total_costing_amount),
# co je pole, ktore ERPNext sam prepocitava pri ulozeni Project dokumentu (update_costing).

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

    projects = frappe.get_all(
        "Project",
        filters={
            "status": ["not in", ["Cancelled"]],
            "company": company,
        },
        fields=["name", "project_name", "gross_margin", "total_billed_amount", "total_costing_amount"],
    )

    roots = []
    for p in projects:
        amount = p.gross_margin
        if not amount and p.total_billed_amount:
            amount = (p.total_billed_amount or 0) - (p.total_costing_amount or 0)

        if not amount or amount <= 0:
            continue

        roots.append({
            "type": "project",
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
# PROJECT SCOPE - roots = faktury projektu, crown = zamestnanci a ich naklad
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
        {"type": "invoice", "label": inv.name, "amount": inv.grand_total}
        for inv in invoices
        if inv.grand_total
    ]

    amount = proj.gross_margin
    if not amount and proj.total_billed_amount:
        amount = (proj.total_billed_amount or 0) - (proj.total_costing_amount or 0)

    trunk = {"label": proj.project_name or project, "amount": amount or 0}

    crown = get_project_employee_earnings(project)

    return {"roots": roots, "trunk": trunk, "crown": crown}


# Zamestnanci a ich naklad na danej zakazke. Project je pole na Timesheet Detail
# (riadok), nie na hlavicke Timesheet. costing_amount = hours * Costing Rate.
def get_project_employee_earnings(project):
    rows = frappe.db.sql(
        """
        SELECT
            ts.employee AS employee,
            ts.employee_name AS employee_name,
            SUM(td.costing_amount) AS amount
        FROM `tabTimesheet Detail` td
        JOIN `tabTimesheet` ts ON ts.name = td.parent
        WHERE td.project = %s AND ts.docstatus = 1
        GROUP BY ts.employee
        """,
        (project,),
        as_dict=True,
    )

    crown = []
    for r in rows:
        if not r.amount or r.amount <= 0:
            continue
        crown.append({
            "type": "employee",
            "label": r.employee_name or r.employee,
            "amount": r.amount,
            "link": {"scope_type": "employee", "scope_name": r.employee},
        })

    return crown


# ----------------------------------------------------------------------
# EMPLOYEE SCOPE - roots = projekty na ktorych pracoval a kolko na nich stal
# firmu, trunk = celkovy naklad na zamestnanca za vsetky projekty dokopy.
# ----------------------------------------------------------------------
def get_employee_scope(employee):
    if not employee:
        frappe.throw(_("scope_name (employee) required"))

    emp = frappe.db.get_value("Employee", employee, ["employee_name"], as_dict=True)
    if not emp:
        frappe.throw(_("Employee not found"))

    rows = frappe.db.sql(
        """
        SELECT
            td.project AS project,
            p.project_name AS project_name,
            SUM(td.costing_amount) AS amount
        FROM `tabTimesheet Detail` td
        JOIN `tabTimesheet` ts ON ts.name = td.parent
        LEFT JOIN `tabProject` p ON p.name = td.project
        WHERE ts.employee = %s AND ts.docstatus = 1 AND td.project IS NOT NULL AND td.project != ''
        GROUP BY td.project
        """,
        (employee,),
        as_dict=True,
    )

    roots = []
    for r in rows:
        if not r.amount or r.amount <= 0:
            continue
        roots.append({
            "type": "project",
            "label": r.project_name or r.project,
            "amount": r.amount,
            "link": {"scope_type": "project", "scope_name": r.project},
        })

    trunk = {
        "label": emp.employee_name or employee,
        "amount": sum(r["amount"] for r in roots),
    }

    # TODO: crown - rozpad podla Activity Type alebo obdobia, ak to bude treba
    crown = []

    return {"roots": roots, "trunk": trunk, "crown": crown}