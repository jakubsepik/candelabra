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

    function handle_scan(text) {
        let parts = text.split(":");
        if (parts.length !== 3 || parts[0] !== "CDLB") {
            frappe.msgprint(__("Neplatný QR formát"));
            return;
        }
        let [, type_code, id] = parts;
        let doctype = frappe.boot.candelabra_type_map_reverse[type_code];
        if (!doctype) {
            frappe.msgprint(__("Neznámy typ: {0}", [type_code]));
            return;
        }
        frappe.db.exists(doctype, id).then(exists => {
            if (exists) {
                frappe.set_route("Form", doctype, id);
            } else {
                frappe.msgprint(__("Dokument {0} {1} neexistuje", [doctype, id]));
            }
        });
    }
};