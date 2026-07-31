// candelabra/candelabra/page/revenue_graph/revenue_graph.js
//
// Frappe Desk Page: vizualizacia rastoveho stromu ako toku penazi, zdola nahor.
//
//   KORENE (dole)  = zakazky, ktore zarobili peniaze
//   KMEN  (stred)  = jeden uzol "Celkovy zisk", spaja vsetky zakazky
//   KORUNA (hore)  = rozdelenie zisku - konkretni ludia alebo oblasti (material, admin, IT, ...)
//
// TATO VERZIA POUZIVA MOCK DATA. Neries logiku ziskavania GL Entries este.
// Bez klikacej interakcie - cisto vizualny strom.
//
// STYLING: vyhradne Frappe CSS premenne (light/dark kompatibilne). Tenke borders
// (0.5px), bez farebnych vyplni - kategoria vetvy je len maly bodkovy indikator.
//
// LAYOUT: korene aj koruna sa balia (wrap) do viac riadkov, ak by presiahli sirku
// platna, aby nic nepretekalo mimo. Ziadne textove popisky riadkov (KORENE/KMEN/KORUNA).


frappe.pages['revenue-graph'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Rastovy strom',
        single_column: true,
    });

    new RastovyStrom(page);
};

class RastovyStrom {
    constructor(page) {
        this.page = page;

        this.dot_color = {
            employee: 'var(--green-500, #29a745)',
            material: 'var(--orange-500, #d4880d)',
            admin: 'var(--gray-500, #8d8d8d)',
            it: 'var(--blue-500, #2490ef)',
            invoicing: 'var(--purple-500, #705ee0)',
            referral: 'var(--pink-500, #e0568c)',
        };

        this.load_mock_data();
        this.render_layout();
        this.draw();
    }

    // ------------------------------------------------------------------
    // MOCK DATA - nahradit neskor frappe.call na GL Entry / Sales Invoice
    // ------------------------------------------------------------------
    load_mock_data() {
        this.roots = [
            { label: 'Web pre Firmu A', amount: 5000 },
            { label: 'Eshop pre Firmu B', amount: 8000 },
            { label: 'Konzultacie Firma C', amount: 3000 },
        ];

        this.total_amount = this.roots.reduce((s, r) => s + r.amount, 0);
        this.trunk = { label: 'Celkovy zisk', amount: this.total_amount };

        this.crown = [
            { type: 'employee', label: 'Sepik', amount: 3500 },
            { type: 'employee', label: 'Jana', amount: 1900 },
            { type: 'employee', label: 'Tomas', amount: 2900 },
            { type: 'material', label: 'Material', amount: 1300 },
            { type: 'admin', label: 'Administrativa', amount: 1700 },
            { type: 'it', label: 'IT / Vyvoj', amount: 2500 },
            { type: 'invoicing', label: 'Fakturacia', amount: 1100 },
            { type: 'referral', label: 'Referent', amount: 1100 },
        ];

        // TODO: nahradit realnym suctom z GL Entries (root = Sales Invoice zisk,
        // crown = distribucne Journal Entry riadky podla Account / Employee dimension)
    }

    render_layout() {
        this.$body = $(`
			<div class="rastovy-strom-wrapper">
				<svg id="rastovy-strom-svg" width="100%"></svg>
				<div class="legend" style="display:flex;gap:16px;font-size:12px;
					color:var(--text-muted);margin-top:8px;flex-wrap:wrap;">
					<span><span class="strom-dot" style="background:${this.dot_color.employee};"></span> zamestnanci</span>
					<span><span class="strom-dot" style="background:${this.dot_color.material};"></span> material</span>
					<span><span class="strom-dot" style="background:${this.dot_color.admin};"></span> administrativa</span>
					<span><span class="strom-dot" style="background:${this.dot_color.it};"></span> IT / vyvoj</span>
					<span><span class="strom-dot" style="background:${this.dot_color.invoicing};"></span> fakturacia</span>
					<span><span class="strom-dot" style="background:${this.dot_color.referral};"></span> referent</span>
				</div>
			</div>
		`).appendTo(this.page.main);

        if (!$('#rastovy-strom-dot-style').length) {
            $('<style id="rastovy-strom-dot-style">.strom-dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:4px;}</style>').appendTo('head');
        }
    }

    // ------------------------------------------------------------------
    // LAYOUT - zabali polozky do viac riadkov, ak by presiahli sirku platna.
    // Vrati pole riadkov, kazdy riadok je pole uzlov s x/w/cx (bez y - to sa
    // prideluje neskor podla poctu riadkov v danej sekcii).
    // ------------------------------------------------------------------
    pack_rows(items, canvas_width, safe_width, gap) {
        const max_amt = Math.max(...items.map((i) => i.amount));
        const w_scale = d3.scaleSqrt().domain([0, max_amt]).range([70, 170]);

        const sized = items.map((item) => ({ ...item, w: w_scale(item.amount) }));

        const rows = [];
        let current = [];
        let current_w = 0;
        sized.forEach((item) => {
            const add_w = current.length ? gap + item.w : item.w;
            if (current_w + add_w > safe_width && current.length > 0) {
                rows.push(current);
                current = [];
                current_w = 0;
            }
            current.push(item);
            current_w += current.length > 1 ? gap + item.w : item.w;
        });
        if (current.length) rows.push(current);

        const margin_x = (canvas_width - safe_width) / 2;
        return rows.map((row) => {
            const total_w = row.reduce((s, n) => s + n.w, 0) + gap * (row.length - 1);
            let x = margin_x + (safe_width - total_w) / 2;
            return row.map((n) => {
                const node = { ...n, x, cx: x + n.w / 2 };
                x += n.w + gap;
                return node;
            });
        });
    }

    link_path(x0, y0, x1, y1) {
        const my = (y0 + y1) / 2;
        return `M${x0},${y0} C${x0},${my} ${x1},${my} ${x1},${y1}`;
    }

    // ------------------------------------------------------------------
    // D3 RENDER - zdola nahor: korene -> kmen -> koruna, viac riadkov ak treba
    // ------------------------------------------------------------------
    draw() {
        const W = 820;
        const safe_width = W - 80;
        const node_h = 46;
        const row_gap = 20;
        const line_gap = 14;
        const section_margin = 40;
        const fmt = (n) => new Intl.NumberFormat('sk-SK').format(Math.round(n));

        const root_rows = this.pack_rows(this.roots, W, safe_width, row_gap);
        const crown_rows = this.pack_rows(this.crown, W, safe_width, row_gap);

        const trunk_w = 190;
        const trunk_h = node_h * 1.3;

        // vyska sekcii podla poctu riadkov
        const crown_h = crown_rows.length * node_h + (crown_rows.length - 1) * line_gap;
        const root_h = root_rows.length * node_h + (root_rows.length - 1) * line_gap;

        // crown je hore, jeho posledny (najspodnejsi) riadok je najblizsie ku kmenu
        const crown_top = 30;
        const trunk_y = crown_top + crown_h + section_margin;
        const root_top = trunk_y + trunk_h + section_margin;
        const total_h = root_top + root_h + 30;

        const svg = d3.select(this.$body.find('#rastovy-strom-svg')[0]);
        svg.selectAll('*').remove();
        svg.attr('viewBox', `0 0 ${W} ${total_h}`);

        const trunk_node = { label: this.trunk.label, amount: this.trunk.amount, x: (W - trunk_w) / 2, cx: W / 2 };

        // prideli absolutne y kazdemu riadku
        const with_row_y = (rows, top) =>
            rows.flatMap((row, i) => row.map((n) => ({ ...n, y: top + i * (node_h + line_gap) })));

        const root_nodes = with_row_y(root_rows, root_top);
        const crown_nodes = with_row_y(crown_rows, crown_top);

        const link_amt_root = d3.scaleLinear().domain([0, d3.max(this.roots, (r) => r.amount)]).range([1.5, 8]);
        const link_amt_crown = d3.scaleLinear().domain([0, d3.max(this.crown, (c) => c.amount)]).range([1.5, 8]);

        const g = svg.append('g');

        g.selectAll('path.root-link')
            .data(root_nodes)
            .enter()
            .append('path')
            .attr('fill', 'none')
            .attr('stroke', 'var(--border-color)')
            .attr('stroke-opacity', 0.8)
            .attr('stroke-width', (d) => link_amt_root(d.amount))
            .attr('d', (d) => this.link_path(d.cx, d.y, trunk_node.cx, trunk_y + trunk_h));

        g.selectAll('path.crown-link')
            .data(crown_nodes)
            .enter()
            .append('path')
            .attr('fill', 'none')
            .attr('stroke', (d) => this.dot_color[d.type])
            .attr('stroke-opacity', 0.4)
            .attr('stroke-width', (d) => link_amt_crown(d.amount))
            .attr('d', (d) => this.link_path(trunk_node.cx, trunk_y, d.cx, d.y + node_h));

        const draw_node = (sel, dot_fn) => {
            sel.attr('transform', (d) => `translate(${d.x},${d.y})`);

            // rozmazany podklad - jemna farebna ziara za uzlom
            sel
                .append('rect')
                .attr('width', (d) => d.w)
                .attr('height', node_h)
                .attr('rx', 6)
                .attr('fill', 'var(--text-color)')
                .attr('fill-opacity', 0.08)
                .attr('filter', 'url(#soft-blur)');

            // ostry vrchny obdlznik - tenky border, takmer priehladna jednotna farba
            sel
                .append('rect')
                .attr('width', (d) => d.w)
                .attr('height', node_h)
                .attr('rx', 6)
                .attr('fill', 'var(--text-color)')
                .attr('fill-opacity', 0.03)
                .attr('stroke', 'var(--border-color)')
                .attr('stroke-width', 0.5);

            if (dot_fn) {
                sel.append('circle').attr('cx', 14).attr('cy', 12).attr('r', 3.5).attr('fill', dot_fn);
            }

            sel
                .append('text')
                .attr('x', (d) => d.w / 2)
                .attr('y', node_h / 2 - 7)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'central')
                .attr('fill', 'var(--text-color)')
                .style('font-size', '13px')
                .style('font-weight', 500)
                .text((d) => (d.label.length > 18 ? d.label.slice(0, 17) + '.' : d.label));

            sel
                .append('text')
                .attr('x', (d) => d.w / 2)
                .attr('y', node_h / 2 + 10)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'central')
                .attr('fill', 'var(--text-muted)')
                .style('font-size', '12px')
                .text((d) => `${fmt(d.amount)} EUR`);
        }

        draw_node(g.selectAll('g.root').data(root_nodes).enter().append('g'), null);

        const trunk_sel = g.append('g').datum(trunk_node).attr('transform', `translate(${trunk_node.x},${trunk_y})`);
        trunk_sel
            .append('rect')
            .attr('width', trunk_w)
            .attr('height', trunk_h)
            .attr('rx', 6)
            .attr('fill', 'var(--fg-color, var(--card-bg))')
            .attr('stroke', 'var(--border-color)')
            .attr('stroke-width', 0.5);
        trunk_sel
            .append('text')
            .attr('x', trunk_w / 2)
            .attr('y', trunk_h / 2 - 8)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'central')
            .attr('fill', 'var(--text-color)')
            .style('font-size', '14px')
            .style('font-weight', 600)
            .text('Celkovy zisk');
        trunk_sel
            .append('text')
            .attr('x', trunk_w / 2)
            .attr('y', trunk_h / 2 + 12)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'central')
            .attr('fill', 'var(--text-muted)')
            .style('font-size', '13px')
            .text(`${fmt(trunk_node.amount)} EUR`);

        draw_node(g.selectAll('g.crown').data(crown_nodes).enter().append('g'), (d) => this.dot_color[d.type]);
    }
}