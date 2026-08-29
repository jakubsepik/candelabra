frappe.pages['qr-scanner'].on_page_load = function (wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('QR Scanner'),
        single_column: true
    });

    let scan_btn = page.set_primary_action(__('Skenovať'), () => start_scan(), 'scan');

    // auto-spusti scanner hneď po vstupe na stránku
    start_scan();

    function start_scan() {
        new frappe.ui.Scanner({
            dialog: true,
            multiple: false,
            on_scan(data) {
                handle_scan(data.decodedText);
            },
            on_error(err) {
                frappe.msgprint(__("Chyba pri skenovaní: {0}", [err]));
            }
        });
    }

    async function handle_scan(text) {
        let parts = text.split(":");

        if (parts[0] !== "CDLB" || parts.length < 2 || parts.length > 3) {
            frappe.msgprint(__("Neplatný QR formát"));
            return;
        }

        let doctype;
        let id;

        if (parts.length === 2) {
            [, id] = parts;

            const r = await frappe.db.get_value(
                "QR Code Link",
                id,
                ["reference_doctype", "reference_name"]
            );

            if (!r?.message?.reference_doctype || !r?.message?.reference_name) {
                frappe.msgprint(
                    __("QR Code Link neexistuje alebo nemá nastavenú referenciu")
                );
                return;
            }

            doctype = r.message.reference_doctype;
            id = r.message.reference_name;

        } else {
            // Formát: CDLB:<TYPE>:<ID>
            let type_code;
            [, type_code, id] = parts;

            doctype = frappe.boot.candelabra_type_map_reverse[type_code];

            if (!doctype) {
                frappe.msgprint(__("Neznámy typ: {0}", [type_code]));
                return;
            }
        }

        const exists = await frappe.db.exists(doctype, id);

        if (exists) {
            frappe.set_route("Form", doctype, id);
        } else {
            frappe.msgprint(
                __("Dokument {0} {1} neexistuje", [doctype, id])
            );
        }
    }
};