function add_qr_export(listview) {
    listview.page.add_actions_menu_item(__('Export QR kódov'), () => {
        const names = listview.get_checked_items(true);
        if (!names.length) {
            frappe.msgprint(__('Vyber aspoň jednu položku'));
            return;
        }

        frappe.call({
            method: 'candelabra.api.qr.export_qr_codes',
            args: {
                doctype: listview.doctype,
                names: JSON.stringify(names),
            },
            callback(r) {
                show_qr_dialog(listview.doctype, r.message, names);
            },
        });
    });
}

function show_qr_dialog(doctype, csv_text, names) {
    const dialog = new frappe.ui.Dialog({
        title: __('QR kódy'),
        fields: [
            {
                fieldtype: 'Code',
                fieldname: 'codes',
                label: __('Kódy'),
                options: 'CSV',
                default: csv_text,
                read_only: 1,
            },
        ],
        primary_action_label: __('Stiahnuť CSV'),
        primary_action() {
            const blob = new Blob([csv_text], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${doctype}_qr_codes.csv`;
            a.click();
            window.URL.revokeObjectURL(url);
            dialog.hide();
        },
        secondary_action_label: __('Stiahnuť QR PDF'),
        secondary_action() {
            const url = `/api/method/candelabra.api.qr.export_qr_pdf?doctype=${encodeURIComponent(doctype)}&names=${encodeURIComponent(JSON.stringify(names))}`;
            window.open(url);
        },
    });

    dialog.show();
}

Object.keys(frappe.boot.candelabra_type_map || {}).forEach((doctype) => {
    frappe.listview_settings[doctype] =
        frappe.listview_settings[doctype] || {};

    const original_onload =
        frappe.listview_settings[doctype].onload;

    frappe.listview_settings[doctype].onload = function (listview) {
        if (original_onload) {
            original_onload(listview);
        }

        add_qr_export(listview);
    };
});