frappe.router.on('change', () => {
    const route = frappe.get_route();
    if (route.length === 1 && route[0] === '') {
        frappe.set_route('desk', 'home');
    }
});