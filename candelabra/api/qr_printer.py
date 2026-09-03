from candelabra.api.qr_generator import generate_custom_qr
import frappe
from urllib.parse import urlencode
from frappe.utils.pdf import get_chrome_pdf

@frappe.whitelist()
def export_to_qr_code_link(doctype, names):
    names = frappe.parse_json(names)

    if doctype == "QR Code Link":
        return "\n".join(names)

    existing = frappe.db.get_all(
        "QR Code Link",
        filters={"reference_doctype": doctype, "reference_name": ["in", names]},
        fields=["name", "reference_name"],
    )
    existing_map = {row.reference_name: row.name for row in existing}

    result = []
    for name in names:
        if name in existing_map:
            result.append(existing_map[name])
        else:
            doc = frappe.get_doc({
                "doctype": "QR Code Link",
                "reference_doctype": doctype,
                "reference_name": name,
            }).insert(ignore_permissions=True)
            result.append(doc.name)

    return "\n".join(result)



import subprocess
import tempfile
import os
from urllib.parse import urlencode

@frappe.whitelist()
def export_qr_code_link_to_pdf(doctype, names):
    names = frappe.parse_json(names)

    if not names:
        frappe.throw("Neboli vybrané žiadne záznamy")

    pages = []

    for name in names:
        name = str(name)
        url = frappe.utils.get_url(
            "/api/method/candelabra.api.qr_redirect.redirect"
        )
        url = f"{url}?{urlencode({'id': name})}"

        img_b64 = generate_custom_qr(url)
        qr_id = frappe.utils.escape_html(name)

        pages.append(f"""
            <section class="qr-page">
                <div class="qr-frame">
                    <div class="qr-image" style="background-image: url('data:image/png;base64,{img_b64}');"></div>
                </div>
                <span class="qr-id">{qr_id}</span>
            </section>
        """)

    html = f"""
    <!doctype html>
    <html>
        <head>
            <meta charset="utf-8">
            <style>
                @import url("https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;700&display=block");

                @page {{
                    size: 62mm 62mm;
                    margin: 0;
                }}

                * {{
                    box-sizing: border-box;
                    margin: 0;
                    padding: 0;
                }}

                .qr-page {{
                    position: relative;
                    width: 62mm;
                    height: 62mm;
                    page-break-after: always;
                }}

                .qr-page:last-child {{
                    page-break-after: avoid;
                }}

                .qr-frame {{
                    position: absolute;
                    top: 3mm;
                    left: 5mm;
                    width: 52mm;
                    height: 52mm;
                    border: 0.4mm solid #000;
                    background: #fff;
                }}

                .qr-image {{
                    position: absolute;
                    top: 2mm;
                    left: 2mm;
                    width: 48mm;
                    height: 48mm;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-size: contain;
                }}

                .qr-id {{
                    position: absolute;
                    top: 53.5mm;
                    left: 50%;
                    z-index: 2;

                    max-width: 46mm;
                    padding: 0 2mm;

                    background: #fff;

                    font-family: "Fira Code", monospace;
                    font-weight: 700;
                    font-size: 3.2mm;
                    line-height: 4mm;
                    letter-spacing: 0.8mm;
                    text-align: center;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;

                    transform: translateX(-50%);
                }}
            </style>
        </head>
        <body>
            {''.join(pages)}
        </body>
    </html>
    """

    pdf_bytes = render_pdf_via_chromium(html)

    if not pdf_bytes:
        frappe.throw("Generovanie PDF zlyhalo")

    safe_doctype = frappe.scrub(str(doctype))
    frappe.local.response.filename = f"{safe_doctype}_qr_codes.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "download"


def render_pdf_via_chromium(html: str) -> bytes:
    chromium_path = frappe.conf.get("chromium_binary_path") or "/usr/bin/chromium"

    if not os.path.exists(chromium_path):
        frappe.throw(f"Chromium binary nenájdený na {chromium_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        html_path = os.path.join(tmp_dir, "input.html")
        pdf_path = os.path.join(tmp_dir, "output.pdf")

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        cmd = [
            chromium_path,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--no-pdf-header-footer",
            "--run-all-compositor-stages-before-draw",
            "--virtual-time-budget=10000",
            f"--print-to-pdf={pdf_path}",
            f"file://{html_path}",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0:
            frappe.log_error(
                title="Chromium PDF generation failed",
                message=result.stderr.decode("utf-8", errors="ignore"),
            )
            frappe.throw("Chromium zlyhal pri generovaní PDF")

        if not os.path.exists(pdf_path):
            frappe.throw("PDF súbor nebol vytvorený")

        with open(pdf_path, "rb") as f:
            return f.read()