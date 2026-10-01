# candelabra/candelabra/api/revenue.py
#
# Backend pre revenue-graph page.
#
# Dva endpointy, obidva vracaju JEDEN JSON objekt s tromi poliami:
#
#   {
#       "trunk": {"label": ..., "amount": ...},
#       "root":  [ node, node, ... ],   # vetva rastuca dolu
#       "crown": [ node, node, ... ],   # vetva rastuca hore
#   }
#
# get_revenue_tree       - firemny (company-wide) pohlad
# get_employee_revenue_tree - pohlad pre jedneho zamestnanca:
#     root  = referraly smerom na neho (zakaznici + zamestnanci, ktorych
#             Referral Code ukazuje na partner_type='Employee', partner=<on>)
#     crown = zakazky (projekty), na ktorych pracoval
#
# Kazdy node, hocijako hlboko v strome, ma jednoduchy tvar:
#
#   {
#       "type": str,           # "project" | "employee" | "invoice" | "referral" | ...
#       "name": str | None,    # nazov dokumentu (Project/Employee/...)
#       "label": str,
#       "amount": number,
#       "link": {...} | None,
#       "nodes": [ ... ],      # dalsie deti, rekurzivne, rovnakeho tvaru
#   }
#
# ROZSIRITELNOST: kazdy typ node-u ma svoj "resolver" - funkciu, ktora pre
# dany node vrati zoznam jeho deti (flat list). Novy typ node-u = napisat
# resolver + zaregistrovat ho cez @register_resolver. Nic ine sa nemusi menit.
#
# Referovany zamestnanec dostava type "employee" (nie "referral"), lebo pre
# "employee" uz existuje resolver - takze sa da rekurzivne rozbalit na jeho
# vlastne zakazky aj jeho vlastne referraly.
#
# PERMISSIONS: docasne odstranene, oba endpointy su zatial bez kontroly,
# kto si smie pozriet ktory pohlad.
#
# CYKLY A HLBKA: employee <-> project je obojsmerny vztah, rozvijanim stromu
# do neobmedzenej hlbky by vznikol nekonecny strom. Riesenie:
#   1. max_depth - tvrdy strop na pocet urovni (parameter API volania)
#   2. cyklova ochrana - ak sa (type, name) uz nachadza v aktualnej vetve
#      od korena, node sa dalej nerozvija
#   3. cache resolvera - vysledok resolvera pre dany (type, name) sa pocita
#      z DB len raz za request

import frappe
from frappe import utils, defaults
from frappe import _

# ----------------------------------------------------------------------
# REGISTER: typ node-u -> resolver funkcia (node) -> list[child_node_dict]
# ----------------------------------------------------------------------
NODE_RESOLVERS = {}

DEFAULT_MAX_DEPTH = 3


def register_resolver(node_type):
    def wrapper(fn):
        NODE_RESOLVERS[node_type] = fn
        return fn
    return wrapper


def make_node(node_type, label, amount, name=None, link=None):
    return {
        "type": node_type,
        "name": name,
        "label": label,
        "amount": amount or 0,
        "link": link,
    }


def build_tree(root_children, crown_children, trunk, max_depth):
    cache = {}
    root = [expand_node(dict(c), max_depth, depth=1, path=set(), cache=cache) for c in root_children]
    crown = [expand_node(dict(c), max_depth, depth=1, path=set(), cache=cache) for c in crown_children]
    return {"trunk": trunk, "root": root, "crown": crown}


def expand_node(node, max_depth, depth, path, cache):
    node["nodes"] = []

    node_key = (node["type"], node.get("name"))
    if depth >= max_depth or node_key in path:
        return node

    resolver = NODE_RESOLVERS.get(node["type"])
    if not resolver:
        return node

    if node_key not in cache:
        cache[node_key] = resolver(node)
    children = cache[node_key]

    next_path = path | {node_key}
    node["nodes"] = [
        expand_node(dict(child), max_depth, depth + 1, next_path, cache)
        for child in children
    ]
    return node


# ----------------------------------------------------------------------
# ENTRY POINTS
# ----------------------------------------------------------------------
@frappe.whitelist()
def get_revenue_tree(max_depth=None):
    max_depth = utils.cint(max_depth) or DEFAULT_MAX_DEPTH
    root_children, crown_children = build_company_root()
    trunk = make_node("trunk", "Candelabra", 0)
    return build_tree(root_children, crown_children, trunk, max_depth)


@frappe.whitelist()
def get_employee_revenue_tree(employee, max_depth=None):
    if not employee:
        frappe.throw(_("employee required"))

    max_depth = utils.cint(max_depth) or DEFAULT_MAX_DEPTH
    root_children, crown_children = build_employee_root(employee)

    emp_name = frappe.db.get_value("Employee", employee, "employee_name")
    trunk = make_node("trunk", emp_name or employee, sum(n["amount"] for n in crown_children))

    return build_tree(root_children, crown_children, trunk, max_depth)


# ----------------------------------------------------------------------
# SHARED HELPERS
# ----------------------------------------------------------------------
def get_all_active_employees():
    return frappe.get_all(
        "Employee",
        filters={"status": "Active"},
        fields=["name", "employee_name"],
        order_by="employee_name asc",
    )


def referral_fields_exist(doctype="Customer"):
    return frappe.db.has_column(doctype, "custom_referral_code")


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


def get_employee_costing(project=None):
    employees = get_all_active_employees()

    if project:
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
    else:
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
        make_node(
            "employee",
            emp.employee_name or emp.name,
            amount_by_employee.get(emp.name, 0),
            name=emp.name,
            link={"doctype": "Employee", "name": emp.name},
        )
        for emp in employees
    ]


def get_single_employee_costing(employee):
    row = frappe.db.sql(
        """
        SELECT SUM(td.costing_amount) AS amount
        FROM `tabTimesheet Detail` td
        JOIN `tabTimesheet` ts ON ts.name = td.parent
        WHERE ts.employee = %s AND ts.docstatus = 1
        """,
        (employee,),
        as_dict=True,
    )
    return (row[0].amount or 0) if row else 0


def get_employee_project_earnings(employee):
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

    nodes = []
    for r in rows:
        if not r.amount or r.amount <= 0:
            continue
        nodes.append(make_node(
            "project",
            r.project_name or r.project,
            r.amount,
            name=r.project,
            link={"doctype": "Project", "name": r.project},
        ))
    return nodes


def get_company_referrals():
    if not referral_fields_exist("Customer"):
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

    nodes = []
    for r in rows:
        cust_name = frappe.db.get_value("Customer", r.ref_name, "customer_name")
        nodes.append(make_node("referral", cust_name or r.ref_name, r.amount, name=r.ref_name))
    return nodes


def get_employee_referred_customers(employee):
    if not referral_fields_exist("Customer"):
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
        make_node("referral", r.customer_name or r.customer, r.amount, name=r.customer)
        for r in rows
    ]


# Zamestnanci, ktorych referoval dany zamestnanec (Employee.custom_referral_code
# -> Referral Code s partner_type='Employee', partner=<employee>). Vracia typ
# "employee", nie "referral" - ma zaregistrovany resolver, takze sa da dalej
# rozbalit (jeho zakazky + jeho vlastne referraly).
def get_employee_referred_employees(employee):
    if not referral_fields_exist("Employee"):
        return []

    rows = frappe.db.sql(
        """
        SELECT e.name AS employee, e.employee_name AS employee_name
        FROM `tabEmployee` e
        JOIN `tabReferral Code` rc ON rc.name = e.custom_referral_code
        WHERE rc.partner_type = 'Employee' AND rc.partner = %s
        """,
        (employee,),
        as_dict=True,
    )

    nodes = []
    for r in rows:
        amount = get_single_employee_costing(r.employee)
        nodes.append(make_node(
            "employee", r.employee_name or r.employee, amount,
            name=r.employee, link={"doctype": "Employee", "name": r.employee},
        ))
    return nodes


# ----------------------------------------------------------------------
# TOP LEVEL - jediné miesto, kde sa deti delia na root/crown. Nie je to
# resolver zaregistrovany v NODE_RESOLVERS, lebo tieto top-level scope-y sa
# nikdy nevyskytuju hlbsie v strome, len tu na vrchu.
# ----------------------------------------------------------------------
def build_company_root():
    profit_map = get_project_profit_map()

    company = defaults.get_user_default("company") or defaults.get_global_default("company")
    filters = {"status": ["!=", "Cancelled"]}
    if company:
        filters["company"] = company

    projects = frappe.get_all("Project", filters=filters, fields=["name", "project_name"])

    root_children = []
    for p in projects:
        amount = profit_map.get(p.name, 0)
        if amount <= 0:
            continue
        root_children.append(make_node(
            "project", p.project_name or p.name, amount,
            name=p.name, link={"doctype": "Project", "name": p.name},
        ))

    crown_children = get_employee_costing() + get_company_referrals()

    return root_children, crown_children


def build_employee_root(employee):
    root_children = get_employee_referred_customers(employee) + get_employee_referred_employees(employee)
    crown_children = get_employee_project_earnings(employee)
    return root_children, crown_children


# ----------------------------------------------------------------------
# RESOLVERS - kazdy vracia FLAT zoznam deti daneho node-u
# ----------------------------------------------------------------------
@register_resolver("project")
def resolve_project(node):
    project = node["name"]

    invoices = frappe.get_all(
        "Sales Invoice",
        filters={"project": project, "docstatus": 1},
        fields=["name", "base_grand_total"],
    )
    invoice_nodes = [
        make_node("invoice", inv.name, inv.base_grand_total, name=inv.name,
                   link={"doctype": "Sales Invoice", "name": inv.name})
        for inv in invoices
    ]

    return invoice_nodes + get_employee_costing(project=project)


@register_resolver("employee")
def resolve_employee(node):
    employee = node["name"]
    return get_employee_project_earnings(employee) + get_employee_referred_customers(employee) + get_employee_referred_employees(employee)

# "invoice" a "referral" nemaju resolver -> su listy stromu. Novy typ node-u
# (napr. rozvinut "referral" na jeho faktury) = pridat @register_resolver.