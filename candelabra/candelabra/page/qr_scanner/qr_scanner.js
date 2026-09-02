
frappe.pages['qr-scanner'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: __('QR Scanner'),
        single_column: true
    });

    page.set_primary_action(__('Skenovať'), start_scan, 'scan');

    // Automaticky spusti scanner
    start_scan();

    function start_scan() {
        new frappe.ui.Scanner({
            dialog: true,
            multiple: false,

            on_scan(data) {
                redirect(data.decodedText);
            },

            on_error(err) {
                frappe.msgprint(
                    __("Chyba pri skenovaní: {0}", [err])
                );
            }
        });
    }

    function redirect(text) {
        try {
            const url = new URL(text);

            if (url.protocol !== "http:" && url.protocol !== "https:") {
                throw new Error("Invalid protocol");
            }

            window.location.href = url.href;
        } catch {
            frappe.msgprint(__("QR kód neobsahuje platnú URL"));
        }
    }
};

