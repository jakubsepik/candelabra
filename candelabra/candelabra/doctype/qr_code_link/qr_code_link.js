frappe.ui.form.on('QR Code Link', {
    setup(frm) {
        const allowed = Object.keys(frappe.boot.candelabra_type_map || {}).filter(dt => dt !== 'QR Code Link');
        frm.set_query('reference_doctype', () => ({
            filters: { name: ['in', allowed] },
        }));
    },
});