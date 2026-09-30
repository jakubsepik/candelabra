// candelabra/candelabra/page/revenue_graph/revenue_graph.js
//
// Frappe Desk Page: vizualizacia rastoveho stromu ako toku penazi, zdola nahor.
//
// KORENE (dole) = zdroje zisku, rekurzivne
// KMEN (stred) = jeden uzol "Celkovy zisk" pre celu firmu
// KORUNA (hore) = zamestnanci a referenti, rekurzivne
//
// FORMAT NODE-u:
// {
//     label: "string",
//     amount: number,
//     type: "employee|material|admin|it|invoicing|referral|project|invoice",
//     link: {
//         doctype: "Project"|"Employee"|"Sales Invoice"|...,
//         name: "DOC-NAME"
//     } | null,
//     nodes: [Node, ...]
// }

const REVENUE_GRAPH_UI = {
    node_html_template: ({ label, amount, type, link, nodes }) => `
        <div class="strom-node-card strom-type-${type}">
            <span class="strom-dot"></span>
            <div class="strom-node-title">${label}</div>
            <div class="strom-node-amount">${amount} EUR</div>
        </div>
    `,

    node_css: `
        .rastovy-strom-wrapper {
            position: relative;
            width: 100%;
            height: 500px;
            overflow: hidden;
        }

        #rastovy-strom-svg {
            display: block;
            position: absolute;
            inset: 0;
            width: 100%;
            height: 100%;

            overflow: hidden;
            cursor: grab;

            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--fg-color, var(--card-bg));

            user-select: none;
            touch-action: none;
        }

        #rastovy-strom-svg:active {
            cursor: grabbing;
        }

        .strom-node-foreign-object {
            overflow: visible;
        }

        .strom-node-card {
            box-sizing: border-box;
            width: 100%;
            height: 100%;

            display: grid;
            grid-template-rows: 16px 14px;
            align-content: center;
            align-items: center;
            row-gap: 2px;

            padding: 6px 10px;

            border: 1px solid var(--border-color);
            border-radius: 6px;

            background: var(--fg-color, var(--card-bg));
            color: var(--text-color);
            font-family: inherit;
        }

        .strom-node-title {
            width: 100%;
            max-width: 100%;
            height: 16px;
            line-height: 16px;

            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            text-align: center;

            font-size: 13px;
            font-weight: 500;
        }

        .strom-node-amount {
            width: 100%;
            height: 14px;
            line-height: 14px;

            overflow: hidden;
            white-space: nowrap;
            text-align: center;

            color: var(--text-muted);
            font-size: 12px;
        }

        .strom-node-clickable {
            cursor: pointer;
        }

        .strom-node-clickable.strom-node-card:hover {
            opacity: 0.8;
        }

        .strom-trunk-node.strom-node-card {
            border-color: var(--dark-border-color, var(--gray-400, #b6b6b6));
            border-width: 2px;
        }

        .strom-trunk-node.strom-node-title {
            font-size: 14px;
            font-weight: 600;
        }

        .strom-trunk-node.strom-node-amount {
            font-size: 13px;
        }
`,

    link: {
        width: 3,
        opacity: 0.65,
        odd_floor_color: 'var(--blue-500, #2490ef)',
        even_floor_color: 'var(--orange-500, #d4880d)',
    },
};


// Samostatna konfiguracia legendy.
// Zobrazuju sa iba typy pouzite v datach.
const REVENUE_GRAPH_LEGEND = {
    items: {
        employee: {
            label: 'zamestnanci',
            class_name: 'strom-type-employee',
        },

        material: {
            label: 'material',
            class_name: 'strom-type-material',
        },

        admin: {
            label: 'administrativa',
            class_name: 'strom-type-admin',
        },

        it: {
            label: 'IT / vyvoj',
            class_name: 'strom-type-it',
        },

        invoicing: {
            label: 'fakturacia',
            class_name: 'strom-type-invoicing',
        },

        referral: {
            label: 'referent',
            class_name: 'strom-type-referral',
        },

        project: {
            label: 'projekt',
            class_name: 'strom-type-project',
        },

        invoice: {
            label: 'faktura',
            class_name: 'strom-type-invoice',
        },
    },

    css: `
        .strom-legend {
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            z-index: 2;

            display: flex;
            gap: 16px;
            flex-wrap: wrap;

            margin: 0;
            padding: 6px 12px;
            border-bottom-left-radius: 6px;
            border-bottom-right-radius: 6px;

            background: rgba(0, 0, 0, 0.35);
            background: color-mix(in srgb, var(--fg-color, var(--card-bg)) 55%, transparent);
            backdrop-filter: blur(4px);
            -webkit-backdrop-filter: blur(4px);
            border-top: 1px solid var(--border-color);

            color: var(--text-muted);
            font-size: 12px;

            pointer-events: none;
        }

        .strom-legend-item {
            pointer-events: auto;
        }

        .strom-legend-item {
            display: inline-flex;
            align-items: center;
        }

        .strom-dot {
            display: inline-block;
            width: 8px;
            height: 8px;
            margin-right: 4px;
            flex: 0 0 8px;
            border-radius: 50%;
            background-color: var(--strom-type-color, var(--border-color));
        }

        .strom-type-employee {
            --strom-type-color: var(--green-500, #29a745);
        }

        .strom-type-material {
            --strom-type-color: var(--orange-500, #d4880d);
        }

        .strom-type-admin {
            --strom-type-color: var(--gray-500, #8d8d8d);
        }

        .strom-type-it {
            --strom-type-color: var(--blue-500, #2490ef);
        }

        .strom-type-invoicing {
            --strom-type-color: var(--purple-500, #705ee0);
        }

        .strom-type-referral {
            --strom-type-color: var(--pink-500, #e0568c);
        }

        .strom-type-project {
            --strom-type-color: var(--yellow-500, #fdb022);
        }

        .strom-type-invoice {
            --strom-type-color: var(--cyan-500, #17a2b8);
        }
`,
};


frappe.pages['revenue-graph'].on_page_load = function (wrapper) {
    const page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Rastovy strom',
        single_column: true,
    });

    wrapper.rastovy_strom = new RastovyStrom(page);
};


frappe.pages['revenue-graph'].on_page_show = function (wrapper) {
    if (wrapper.rastovy_strom) {
        wrapper.rastovy_strom.load_and_draw();
    }
};


class RastovyStrom {
    constructor(page) {
        this.page = page;

        this.roots = [];

        this.trunk = {
            label: '',
            amount: 0,
        };

        this.crown = [];

        this.render_skeleton();
    }


    // Vytvori zakladne HTML iba raz.
    render_skeleton() {
        this.$body = $(`
            <div class="rastovy-strom-wrapper">
                <svg id="rastovy-strom-svg"></svg>

                <div class="strom-legend"></div>
            </div>
        `).appendTo(this.page.main);

        if (!$('#rastovy-strom-node-style').length) {
            $('<style id="rastovy-strom-node-style"></style>')
                .text(
                    REVENUE_GRAPH_UI.node_css +
                    REVENUE_GRAPH_LEGEND.css
                )
                .appendTo('head');
        }

        this.load_and_draw();
    }


    collect_used_types(
        items,
        used_types = new Set()
    ) {
        (items || []).forEach((node) => {
            if (
                node.type &&
                REVENUE_GRAPH_LEGEND.items[node.type]
            ) {
                used_types.add(node.type);
            }

            this.collect_used_types(
                node.nodes,
                used_types
            );
        });

        return used_types;
    }


    render_legend() {
        const used_types =
            this.collect_used_types([
                ...this.roots,
                ...this.crown,
            ]);

        const $legend = this.$body
            .find('.strom-legend')
            .empty();

        Object.entries(
            REVENUE_GRAPH_LEGEND.items
        ).forEach(([type, item]) => {
            if (!used_types.has(type)) {
                return;
            }

            $('<span>')
                .addClass(
                    `strom-legend-item ${item.class_name}`
                )
                .append(
                    $('<span>')
                        .addClass('strom-dot')
                        .attr(
                            'aria-hidden',
                            'true'
                        )
                )
                .append(
                    $('<span>').text(
                        item.label
                    )
                )
                .appendTo($legend);
        });

        $legend.toggle(
            used_types.size > 0
        );
    }


    load_and_draw() {
        frappe.call({
            method:
                'candelabra.api.revenue.get_revenue_tree',

            freeze: true,

            callback: (response) => {
                if (!response.message) {
                    return;
                }

                this.roots =
                    response.message.root ||
                    response.message.roots ||
                    [];

                this.trunk =
                    response.message.trunk || {
                        label: 'Celkovy zisk',
                        amount: 0,
                    };

                this.crown =
                    response.message.crown ||
                    [];

                this.render_legend();

                if (
                    !this.roots.length &&
                    !this.crown.length
                ) {
                    this.show_empty_state();

                    frappe.show_alert({
                        message: __(
                            'Ziadne data pre dany vyber'
                        ),
                        indicator: 'orange',
                    });

                    return;
                }

                this.draw();
            },
        });
    }


    show_empty_state() {
        this.$body
            .find('#rastovy-strom-svg')
            .empty();
    }


    // Amount moze byt cislo alebo objekt
    // vo formate { source, parsedValue }.
    norm_amount(value) {
        if (
            value &&
            typeof value === 'object'
        ) {
            return value.parsedValue || 0;
        }

        return value || 0;
    }


    // Rozbali rekurzivny strom na pole urovni.
    flatten_levels(items, side) {
        const levels = [];

        let current = items.map(
            (node) => ({
                ...node,

                amount: this.norm_amount(
                    node.amount
                ),

                parent: null,
                depth: 0,
                side,
            })
        );

        while (current.length) {
            levels.push(current);

            const next = [];

            current.forEach((wrapper) => {
                (
                    wrapper.nodes || []
                ).forEach((child) => {
                    next.push({
                        ...child,

                        amount:
                            this.norm_amount(
                                child.amount
                            ),

                        parent: wrapper,

                        depth:
                            wrapper.depth + 1,

                        side,
                    });
                });
            });

            current = next;
        }

        return levels;
    }


    // Vypocita potrebnu sirku jedneho poschodia.
    measure_level_width(items, gap) {
        if (!items.length) {
            return 0;
        }

        const max_amount = Math.max(
            1,
            ...items.map(
                (item) =>
                    item.amount || 0
            )
        );

        const width_scale = d3
            .scaleSqrt()
            .domain([0, max_amount])
            .range([70, 170]);

        return (
            items.reduce(
                (sum, item) =>
                    sum +
                    width_scale(
                        item.amount || 0
                    ),
                0
            ) +
            gap *
            Math.max(
                0,
                items.length - 1
            )
        );
    }


    // Rozlozi nody v ramci poschodia.
    pack_rows(
        items,
        canvas_width,
        safe_width,
        gap
    ) {
        const max_amount = Math.max(
            1,
            ...items.map(
                (item) =>
                    item.amount || 0
            )
        );

        const width_scale = d3
            .scaleSqrt()
            .domain([0, max_amount])
            .range([70, 170]);

        items.forEach((item) => {
            item.w = width_scale(
                item.amount || 0
            );
        });

        const rows = [];

        let current = [];
        let current_width = 0;

        items.forEach((item) => {
            const added_width =
                current.length
                    ? gap + item.w
                    : item.w;

            if (
                current_width +
                added_width >
                safe_width &&
                current.length > 0
            ) {
                rows.push(current);

                current = [];
                current_width = 0;
            }

            current.push(item);

            current_width +=
                current.length > 1
                    ? gap + item.w
                    : item.w;
        });

        if (current.length) {
            rows.push(current);
        }

        const margin_x =
            (
                canvas_width -
                safe_width
            ) / 2;

        rows.forEach((row) => {
            const total_width =
                row.reduce(
                    (sum, node) =>
                        sum + node.w,
                    0
                ) +
                gap *
                (row.length - 1);

            let x =
                margin_x +
                (
                    safe_width -
                    total_width
                ) / 2;

            row.forEach((node) => {
                node.x = x;
                node.cx =
                    x + node.w / 2;

                x += node.w + gap;
            });
        });

        return rows;
    }


    assign_row_y(
        rows,
        top,
        node_height,
        line_gap
    ) {
        rows.forEach((row, index) => {
            const y =
                top +
                index *
                (
                    node_height +
                    line_gap
                );

            row.forEach((node) => {
                node.y = y;
            });
        });
    }


    link_path(x0, y0, x1, y1) {
        const middle_y =
            (y0 + y1) / 2;

        return (
            `M${x0},${y0} ` +
            `C${x0},${middle_y} ` +
            `${x1},${middle_y} ` +
            `${x1},${y1} `
        );
    }


    escape_html(value) {
        return $('<div>')
            .text(String(value ?? ''))
            .html();
    }


    node_html(node, format_amount) {
        return (
            REVENUE_GRAPH_UI
                .node_html_template({
                    label:
                        this.escape_html(
                            node.label ||
                            ''
                        ),

                    amount:
                        this.escape_html(
                            format_amount(
                                node.amount
                            )
                        ),

                    type:
                        this.escape_html(
                            node.type ||
                            ''
                        ),

                    depth: node.depth,
                    side: node.side,
                })
        );
    }


    // Poschodie 1 je spojenie kmena s depth 0.
    floor_link_color(node) {
        const floor =
            (node.depth || 0) + 1;

        return floor % 2 === 0
            ? REVENUE_GRAPH_UI
                .link.even_floor_color
            : REVENUE_GRAPH_UI
                .link.odd_floor_color;
    }


    navigate_to(node) {
        if (
            !node.link ||
            !node.link.doctype ||
            !node.link.name
        ) {
            return;
        }

        frappe.set_route(
            'Form',
            node.link.doctype,
            node.link.name
        );
    }


    draw() {
        if (
            !this.roots.length &&
            !this.crown.length
        ) {
            this.show_empty_state();
            return;
        }

        const node_height = 46;
        const row_gap = 20;
        const line_gap = 14;
        const section_margin = 40;
        const level_margin = 30;

        const format_amount = (number) =>
            new Intl.NumberFormat(
                'sk-SK'
            ).format(
                Math.round(number || 0)
            );

        const root_levels =
            this.roots.length
                ? this.flatten_levels(
                    this.roots,
                    'root'
                )
                : [];

        const crown_levels =
            this.crown.length
                ? this.flatten_levels(
                    this.crown,
                    'crown'
                )
                : [];

        // Virtualna sirka stromu.
        const level_widths = [
            ...root_levels,
            ...crown_levels,
        ].map((items) =>
            this.measure_level_width(
                items,
                row_gap
            )
        );

        const canvas_width = Math.max(
            820,
            Math.ceil(
                Math.max(
                    0,
                    ...level_widths
                ) + 80
            )
        );

        const safe_width =
            canvas_width - 80;

        const layout_level = (items) => {
            const rows = this.pack_rows(
                items,
                canvas_width,
                safe_width,
                row_gap
            );

            const height = rows.length
                ? rows.length *
                node_height +
                (
                    rows.length - 1
                ) *
                line_gap
                : 0;

            return {
                rows,
                h: height,
            };
        };

        const root_layouts =
            root_levels.map(
                layout_level
            );

        const crown_layouts =
            crown_levels.map(
                layout_level
            );

        const root_height_total =
            root_layouts.reduce(
                (
                    sum,
                    layout,
                    index
                ) =>
                    sum +
                    layout.h +
                    (
                        index
                            ? level_margin
                            : 0
                    ),
                0
            );

        const crown_height_total =
            crown_layouts.reduce(
                (
                    sum,
                    layout,
                    index
                ) =>
                    sum +
                    layout.h +
                    (
                        index
                            ? level_margin
                            : 0
                    ),
                0
            );

        const trunk_width = 190;

        const trunk_height =
            node_height * 1.3;

        const crown_top = 30;

        const trunk_y =
            crown_top +
            crown_height_total +
            (
                crown_layouts.length
                    ? section_margin
                    : 0
            );

        const root_top =
            trunk_y +
            trunk_height +
            (
                root_layouts.length
                    ? section_margin
                    : 0
            );

        const total_height =
            root_top +
            root_height_total +
            30;

        // Koruna: najhlbsia uroven je hore.
        // Uroven 0 je najblizsie ku kmenu.
        let y_cursor = crown_top;

        const crown_level_y =
            new Array(
                crown_layouts.length
            );

        for (
            let index =
                crown_layouts.length - 1;
            index >= 0;
            index -= 1
        ) {
            crown_level_y[index] =
                y_cursor;

            y_cursor +=
                crown_layouts[index].h +
                level_margin;
        }

        // Korene: uroven 0 je priamo pod kmenom.
        y_cursor = root_top;

        const root_level_y =
            new Array(
                root_layouts.length
            );

        for (
            let index = 0;
            index <
            root_layouts.length;
            index += 1
        ) {
            root_level_y[index] =
                y_cursor;

            y_cursor +=
                root_layouts[index].h +
                level_margin;
        }

        root_layouts.forEach(
            (layout, index) => {
                this.assign_row_y(
                    layout.rows,
                    root_level_y[
                    index
                    ],
                    node_height,
                    line_gap
                );
            }
        );

        crown_layouts.forEach(
            (layout, index) => {
                this.assign_row_y(
                    layout.rows,
                    crown_level_y[
                    index
                    ],
                    node_height,
                    line_gap
                );
            }
        );

        const root_nodes =
            root_layouts.flatMap(
                (layout) =>
                    layout.rows.flat()
            );

        const crown_nodes =
            crown_layouts.flatMap(
                (layout) =>
                    layout.rows.flat()
            );

        // Pouzivame priamo DOM element.
        // Takto sa vyhneme svg.node() === null.
        const svg_element = this.$body
            .find('#rastovy-strom-svg')
            .get(0);

        if (!svg_element) {
            return;
        }

        const svg = d3.select(
            svg_element
        );

        // Odstran predchadzajuci obsah.
        svg.selectAll('*').remove();

        // Odstran predchadzajuce D3 zoom eventy.
        svg.on('.zoom', null);

        // SVG je iba viewport.
        // Fyzicku velkost urcuje CSS.
        svg.attr('viewBox', null);

        const trunk_node = {
            label: this.trunk.label,

            amount: this.norm_amount(
                this.trunk.amount
            ),

            x:
                (
                    canvas_width -
                    trunk_width
                ) / 2,

            cx: canvas_width / 2,
            y: trunk_y,

            w: trunk_width,
            h: trunk_height,

            type: 'trunk',
            side: 'trunk',
            depth: 0,
        };

        // Vsetok obsah grafu je v jednom G.
        // D3 zoom transformuje tento element.
        const graph = svg.append('g');

        const zoom = d3
            .zoom()
            .scaleExtent([0.15, 4])
            .on('zoom', (event) => {
                graph.attr(
                    'transform',
                    event.transform
                );
            });

        // Aktivuje:
        // - drag = pan
        // - wheel = zoom
        svg.call(zoom);


        // ---------------------------------------------------------
        // ROOT LINKS
        // ---------------------------------------------------------

        if (root_nodes.length) {
            graph
                .selectAll(
                    'path.root-link'
                )
                .data(root_nodes)
                .enter()
                .append('path')
                .attr('fill', 'none')
                .attr(
                    'stroke',
                    (node) =>
                        this.floor_link_color(
                            node
                        )
                )
                .attr(
                    'stroke-opacity',
                    REVENUE_GRAPH_UI
                        .link.opacity
                )
                .attr(
                    'stroke-width',
                    REVENUE_GRAPH_UI
                        .link.width
                )
                .attr(
                    'd',
                    (node) => {
                        const parent_center_x =
                            node.parent
                                ? node
                                    .parent
                                    .cx
                                : trunk_node
                                    .cx;

                        const parent_bottom =
                            node.parent
                                ? node
                                    .parent
                                    .y +
                                node_height
                                : trunk_y +
                                trunk_height;

                        return this.link_path(
                            node.cx,
                            node.y,
                            parent_center_x,
                            parent_bottom
                        );
                    }
                );
        }


        // ---------------------------------------------------------
        // CROWN LINKS
        // ---------------------------------------------------------

        if (crown_nodes.length) {
            graph
                .selectAll(
                    'path.crown-link'
                )
                .data(crown_nodes)
                .enter()
                .append('path')
                .attr('fill', 'none')
                .attr(
                    'stroke',
                    (node) =>
                        this.floor_link_color(
                            node
                        )
                )
                .attr(
                    'stroke-opacity',
                    REVENUE_GRAPH_UI
                        .link.opacity
                )
                .attr(
                    'stroke-width',
                    REVENUE_GRAPH_UI
                        .link.width
                )
                .attr(
                    'd',
                    (node) => {
                        const parent_center_x =
                            node.parent
                                ? node
                                    .parent
                                    .cx
                                : trunk_node
                                    .cx;

                        const parent_top =
                            node.parent
                                ? node
                                    .parent
                                    .y
                                : trunk_y;

                        return this.link_path(
                            parent_center_x,
                            parent_top,
                            node.cx,
                            node.y +
                            node_height
                        );
                    }
                );
        }


        // ---------------------------------------------------------
        // NODE RENDERER
        // ---------------------------------------------------------

        const draw_node = (selection) => {
            selection
                .attr(
                    'transform',
                    (node) =>
                        `translate(${node.x}, ${node.y})`
                )
                .classed(
                    'strom-node-clickable',
                    (node) =>
                        Boolean(
                            node.link &&
                            node.link.name
                        )
                )
                .on(
                    'click',
                    (
                        event,
                        node
                    ) =>
                        this.navigate_to(
                            node
                        )
                );

            selection
                .append(
                    'foreignObject'
                )
                .attr(
                    'class',
                    'strom-node-foreign-object'
                )
                .attr(
                    'width',
                    (node) => node.w
                )
                .attr(
                    'height',
                    (node) =>
                        node.h ||
                        node_height
                )
                .append('xhtml:div')
                .style(
                    'width',
                    '100%'
                )
                .style(
                    'height',
                    '100%'
                )
                .html(
                    (node) =>
                        this.node_html(
                            node,
                            format_amount
                        )
                );
        };


        // ---------------------------------------------------------
        // ROOT NODES
        // ---------------------------------------------------------

        if (root_nodes.length) {
            draw_node(
                graph
                    .selectAll('g.root')
                    .data(root_nodes)
                    .enter()
                    .append('g')
            );
        }


        // ---------------------------------------------------------
        // TRUNK NODE
        // ---------------------------------------------------------

        draw_node(
            graph
                .append('g')
                .datum(trunk_node)
                .classed(
                    'strom-trunk-node',
                    true
                )
        );


        // ---------------------------------------------------------
        // CROWN NODES
        // ---------------------------------------------------------

        if (crown_nodes.length) {
            draw_node(
                graph
                    .selectAll('g.crown')
                    .data(crown_nodes)
                    .enter()
                    .append('g')
            );
        }


        // ---------------------------------------------------------
        // INITIAL FIT
        // ---------------------------------------------------------
        //
        // Dolezite:
        // nepouzivame svg.node(), ale priamo svg_element,
        // ktory sme overili vyssie.

        const viewport_width =
            svg_element.clientWidth;

        const viewport_height =
            svg_element.clientHeight;

        // Ak SVG este nema layout rozmery,
        // initial fit preskocime.
        // Samotny graf je ale uz vykresleny.
        if (
            !viewport_width ||
            !viewport_height
        ) {
            return;
        }

        const padding = 40;

        const available_width =
            Math.max(
                1,
                viewport_width -
                padding * 2
            );

        const available_height =
            Math.max(
                1,
                viewport_height -
                padding * 2
            );

        const fit_scale = Math.min(
            available_width /
            canvas_width,

            available_height /
            total_height,

            // Malicky strom automaticky
            // nezvacsi nad 100 %.
            1
        );

        // Musi sediet s dolnym limitom
        // scaleExtent().
        const initial_scale =
            Math.max(
                0.15,
                fit_scale
            );

        // Centrovanie virtualneho canvasu
        // do realneho SVG viewportu.
        const translate_x =
            (
                viewport_width -
                canvas_width *
                initial_scale
            ) / 2;

        const translate_y =
            (
                viewport_height -
                total_height *
                initial_scale
            ) / 2;

        const initial_transform =
            d3.zoomIdentity
                .translate(
                    translate_x,
                    translate_y
                )
                .scale(
                    initial_scale
                );

        svg.call(
            zoom.transform,
            initial_transform
        );
    }
}