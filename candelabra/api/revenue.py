# candelabra/candelabra/api/revenue.py
#
# Backend pre revenue-graph page. Kazda funkcia vracia {"roots": [...], "trunk": {...}, "crown": [...]}
# vo formate, ktory ocakava revenue_graph.js (label, amount, type, volitelne link).
#
# KAZDY node (root aj crown) ma pole "type". Existujuce typy: employee, material,
# admin, it, invoicing, referral, project, invoice.
#
# Zisk projektu sa pocita priamo z dokladov (Sales Invoice minus Timesheet costing),
# nie z poli Projectu, ktore sa v produkcii nemusia prepocitat.
#
# Roots (projekty) sa zobrazuju len ak maju zisk vacsi ako 0.
# Crown (zamestnanci, referenti) sa zobrazuje VZDY, aj ked nie je ziadny projekt
# a aj s amount=0.
#
# REFERRAL - Customer.custom_referral_code (Link na doctype Referral Code).
# Referral Code ma partner_type (Customer/Employee) a partner (Dynamic Link).
# Ak pole neexistuje, referral funkcie vratia prazdny zoznam.

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
    roles = frappe.get_roles()
    if "System Manager" in roles or "Accounts Manager" in roles:
        return

    if scope_type == "employee":
        user_employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
        if not user_employee or user_employee != scope_name:
            frappe.throw(_("Not permitted"), frappe.PermissionError)
        return

    frappe.throw(_("Not permitted"), frappe.PermissionError)


def get_all_active_employees():
    return frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name"],
        order_by="employee_name asc",
    )


def referral_fields_exist():
    return frappe.db.has_column("Customer", "custom_referral_code")


# Zisk kazdeho projektu = suma submitnutych faktur - suma costing_amount z submitnutych
# timesheetov. Vracia dict {project_name: zisk}.
def get_project_profit_map():
    billed = frappe.db.sql(
        """
        SELECT project, SUM(base_grand_total) AS amt
        FROM `tabSales Invoice`
        WHERE docstatus = 1 AND project IS NOT NULL AND project != ''
        GROUP BY project
        """,
        as_dict=True,
    )
    cost = frappe.db.sql(
        """
        SELECT td.project AS project, SUM(td.costing_amount) AS amt
        FROM `tabTimesheet Detail` td
        JOIN `tabTimesheet` ts ON ts.name = td.parent
        WHERE ts.docstatus = 1 AND td.project IS NOT NULL AND td.project != ''
        GROUP BY td.project
        """,
        as_dict=True,
    )
    b = {r.project: (r.amt or 0) for r in billed}
    c = {r.project: (r.amt or 0) for r in cost}
    return {p: b.get(p, 0) - c.get(p, 0) for p in set(b) | set(c)}


# ----------------------------------------------------------------------
# COMPANY SCOPE - roots = projekty s realnym ziskom, crown = vsetci aktivni
# zamestnanci (naklad zo vsetkych timesheetov, aj 0) + referenti zakaznici
# ----------------------------------------------------------------------
def get_company_scope():
    company = frappe.defaults.get_user_default("company") or frappe.defaults.get_global_default("company")

    filters = {"status": ["!=", "Cancelled"]}
    if company:
        filters["company"] = company

    projects = frappe.get_all("Project", filters=filters, fields=["name", "project_name"])
    profit_map = get_project_profit_map()

    roots = []
    for p in projects:
        amount = profit_map.get(p.name, 0)
        if amount <= 0:
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

    crown = get_company_employee_costing() + get_company_referrals()

    return {"roots": roots, "trunk": trunk, "crown": crown}


# Vsetci aktivni zamestnanci a ich celkovy naklad za vsetky projekty dokopy.
# Zamestnanec bez odpracovanych hodin sa zobrazi s amount=0.
def get_company_employee_costing():
    employees = get_all_active_employees()

    rows = frappe.db.sql(
        """
        SELECT ts.employee AS employee, SUM(td.costing_amount) AS amount
        FROM `tabTimesheet Detail` td
        JOIN `tabTimesheet` ts ON ts.name = td.parent
        WHERE ts.docstatus = 1
        GROUP BY ts.employee
        """,
        as_dict=True,
    )
    amount_by_employee = {r.employee: (r.amount or 0) for r in rows}

    return [
        {
            "type": "employee",
            "label": emp.employee_name or emp.name,
            "amount": amount_by_employee.get(emp.name, 0),
            "link": {"scope_type": "employee", "scope_name": emp.name},
        }
        for emp in employees
    ]


# Referenti v company scope: partneri typu Customer. Zamestnanci sa zobrazuju uz cez
# get_company_employee_costing, aby neboli v grafe dvakrat.
# Referent sa zobrazi aj s amount=0 (ak jeho referovani zakaznici nemaju faktury).
# Cesta: Referral Code.partner -> Customer.custom_referral_code -> Sales Invoice
def get_company_referrals():
    if not referral_fields_exist():
        return []

    rows = frappe.db.sql(
        """
        SELECT
            rc.partner AS ref_name,
            COALESCE(SUM(si.base_grand_total), 0) AS amount
        FROM `tabReferral Code` rc
        LEFT JOIN `tabCustomer` c ON c.custom_referral_code = rc.name
        LEFT JOIN `tabSales Invoice` si ON si.customer = c.name AND si.docstatus = 1
        WHERE rc.partner_type = 'Customer'
            AND rc.partner IS NOT NULL AND rc.partner != ''
        GROUP BY rc.partner
        ORDER BY amount DESC
        """,
        as_dict=True,
    )

    crown = []
    for r in rows:
        cust_name = frappe.db.get_value("Customer", r.ref_name, "customer_name")
        crown.append({
            "type": "referral",
            "label": cust_name or r.ref_name,
            "amount": r.amount or 0,
            # ziadny link - customer scope v grafe zatial neexistuje
        })
    return crown


# ----------------------------------------------------------------------
# PROJECT SCOPE - roots = faktury projektu, crown = vsetci zamestnanci a ich
# naklad na tomto konkretnom projekte (0 ak nepracovali)
# ----------------------------------------------------------------------
def get_project_scope(project):
    if not project:
        frappe.throw(_("scope_name (project) required"))

    proj = frappe.db.get_value("Project", project, ["project_name"], as_dict=True)
    if not proj:
        frappe.throw(_("Project not found"))

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"project": project, "docstatus": 1},
        fields=["name", "base_grand_total"],
    )

    roots = [
        {"type": "invoice", "label": inv.name, "amount": inv.base_grand_total or 0}
        for inv in invoices
    ]

    trunk = {
        "label": proj.project_name or project,
        "amount": get_project_profit_map().get(project, 0),
    }

    crown = get_project_employee_earnings(project)

    return {"roots": roots, "trunk": trunk, "crown": crown}


def get_project_employee_earnings(project):
    employees = get_all_active_employees()

    rows = frappe.db.sql(
        """
        SELECT ts.employee AS employee, SUM(td.costing_amount) AS amount
        FROM `tabTimesheet Detail` td
        JOIN `tabTimesheet` ts ON ts.name = td.parent
        WHERE td.project = %s AND ts.docstatus = 1
        GROUP BY ts.employee
        """,
        (project,),
        as_dict=True,
    )
    amount_by_employee = {r.employee: (r.amount or 0) for r in rows}

    return [
        {
            "type": "employee",
            "label": emp.employee_name or emp.name,
            "amount": amount_by_employee.get(emp.name, 0),
            "link": {"scope_type": "employee", "scope_name": emp.name},
        }
        for emp in employees
    ]


# ----------------------------------------------------------------------
# EMPLOYEE SCOPE - roots = projekty s nakladom zamestnanca vacsim ako 0,
# trunk = celkovy naklad na zamestnanca, crown = zakaznici, ktorych
# zamestnanec referoval (cez Referral Code) a ich trzba
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

    crown = get_employee_referred_customers(employee)

    return {"roots": roots, "trunk": trunk, "crown": crown}


# Zakaznici referovani danym zamestnancom a ich celkova trzba.
# Zakaznik bez faktury sa zobrazi s amount=0.
def get_employee_referred_customers(employee):
    if not referral_fields_exist():
        return []

    rows = frappe.db.sql(
        """
        SELECT
            c.name AS customer,
            c.customer_name AS customer_name,
            COALESCE(SUM(si.base_grand_total), 0) AS amount
        FROM `tabCustomer` c
        JOIN `tabReferral Code` rc ON rc.name = c.custom_referral_code
        LEFT JOIN `tabSales Invoice` si ON si.customer = c.name AND si.docstatus = 1
        WHERE rc.partner_type = 'Employee' AND rc.partner = %s
        GROUP BY c.name, c.customer_name
        ORDER BY amount DESC, c.customer_name ASC
        """,
        (employee,),
        as_dict=True,
    )

    return [
        {
            "type": "referral",
            "label": r.customer_name or r.customer,
            "amount": r.amount or 0,
        }
        for r in rows
    ]