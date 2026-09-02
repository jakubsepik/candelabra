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



@frappe.whitelist()
def export_qr_code_link_to_pdf(doctype, names):
    names = frappe.parse_json(names)

    if not names:
        frappe.throw("Neboli vybrané žiadne záznamy")

    pages = []

    for name in names:
        name = str(name)
        url =frappe.utils.get_url( # type: ignore
            "/api/method/candelabra.api.qr_redirect.redirect"
            )
        url = f"{url}?{urlencode({'id': name})}"

        img_b64 = generate_custom_qr(url)
        qr_id = frappe.utils.escape_html(name) # type: ignore

        pages.append(f"""
            <section class="qr-page">
                <div class="qr-frame">
                    <div
                        class="qr-image"
                        style="
                            background-image:
                            url('data:image/png;base64,{img_b64}');
                        "
                    ></div>

                    <span class="qr-id">{qr_id}</span>
                </div>
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
                    size: 162mm 162mm;
                    margin: 0;
                }}

                * {{
                    box-sizing: border-box;
                }}

                html,
                body {{
                    width: 162mm;
                    margin: 0 !important;
                    padding: 0 !important;
                }}

                .qr-page {{
                    position: relative;
                    display: block;

                    width: 162mm;
                    height: 160mm;

                    margin: 0 !important;
                    padding: 0 !important;
                    overflow: hidden;

                    page-break-inside: avoid;
                }}

                .qr-page + .qr-page {{
                    page-break-before: always;
                }}

                .qr-frame {{
                    position: absolute;

                    top: 50mm;
                    left: 81mm;

                    width: 78mm;
                    height: 78mm;

                    margin: 0;
                    padding: 0;

                    border: 0.6mm solid #000;
                    background-color: #fff;

                    transform: translate(-50%, -50%);

                    page-break-inside: avoid !important;
                    break-inside: avoid !important;
                }}

                .qr-image {{
                    position: absolute;
                    top: 3.4mm;
                    left: 3.4mm;

                    width: 70mm;
                    height: 70mm;

                    margin: 0;
                    padding: 0;

                    background-color: #fff;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-size: contain;
                }}

                .qr-id {{
                    position: absolute;
                    left: 50%;
                    bottom: -2.5mm;
                    z-index: 2;

                    display: block;
                    max-width: 70mm;
                    padding: 0 3mm;

                    overflow: hidden;

                    background: #fff;
                    color: #000;

                    font-family: "Fira Code", monospace;
                    font-size: 4mm;
                    font-weight: 700;
                    line-height: 5mm;

                    text-align: center;
                    white-space: nowrap;
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

    pdf_bytes = get_chrome_pdf(
        print_format=None,
        html=html,
        options={
            "page-size": "Custom",
            "page-width": "162mm",
            "page-height": "162mm",
            "margin-top": "0mm",
            "margin-bottom": "0mm",
            "margin-left": "0mm",
            "margin-right": "0mm",
            "print-background": True,
        },
        output=None,
        pdf_generator="chrome",
    )

    if not pdf_bytes:
        frappe.throw("Generovanie PDF zlyhalo")

    safe_doctype = frappe.scrub(str(doctype))

    frappe.local.response.filename = f"{safe_doctype}_qr_codes.pdf"
    frappe.local.response.filecontent = pdf_bytes
    frappe.local.response.type = "download"