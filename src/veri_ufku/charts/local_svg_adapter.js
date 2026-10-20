// Packaged local-svg/v1 adapter. No fetch, external script, eval or network API.
(() => {
    const data = JSON.parse(document.getElementById('dashboard-data').textContent);
    const widgets = new Map(data.widgets.map(w => [w.id, w]));
    function transfer(source, rows, target) {
        if (source === target) return new Set(rows);
        const mappings = Object.values(data.mappings).filter(m => m.source_version === source && m.target_version === target);
        if (!mappings.length) return new Set();
        const token = (version, row, side) => {
            const values = mappings.map(m => (data.keys[version]?.[m[side + '_column']] || {})[row]);
            return values.some(v => v == null) ? null : JSON.stringify(values);
        };
        const keys = new Set(rows.map(r => token(source, r, 'source')).filter(v => v !== null));
        const targetRows = new Set([].concat(...data.widgets.filter(w => w.dataset_version === target).map(w => w.row_ids)));
        return new Set([...targetRows].filter(r => keys.has(token(target, r, 'target'))));
    }
    function select(source, rows) {
        for (const panel of document.querySelectorAll('section[data-widget]')) {
            const widget = widgets.get(panel.dataset.widget);
            const selected = transfer(source, rows, widget.dataset_version);
            const count = widget.row_ids.filter(r => selected.has(r)).length;
            panel.querySelector('.selection').textContent = count + ' bağlantılı RowId seçildi';
            for (const row of panel.querySelectorAll('tr[data-row]')) row.classList.toggle('selected', selected.has(row.dataset.row));
            const img = panel.querySelector('img');
            if (img) img.style.outline = count ? '3px solid #B45309' : '';
        }
    }
    for (const panel of document.querySelectorAll('section[data-widget]')) {
        const widget = widgets.get(panel.dataset.widget);
        for (const row of panel.querySelectorAll('tr[data-row]')) {
            const activate = () => select(widget.dataset_version, [row.dataset.row]);
            row.addEventListener('click', activate);
            row.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') {e.preventDefault(); activate();} });
        }
        const img = panel.querySelector('img');
        if (img) img.addEventListener('click', e => {
            const rect = img.getBoundingClientRect(), metadata = widget.render;
            const x = (e.clientX - rect.left) / rect.width * metadata.width;
            const y = (e.clientY - rect.top) / rect.height * metadata.height;
            const hit = metadata.hit_regions?.find(p => p.left <= x && p.right >= x && p.top <= y && p.bottom >= y);
            const pixel = metadata.pixels?.find(p => Math.hypot(p.x - x, p.y - y) <= 10);
            const id = hit?.point_id ?? pixel?.point_id;
            if (id !== undefined) select(widget.dataset_version, widget.memberships[String(id)] || []);
        });
    }
    document.getElementById('clear').addEventListener('click', () => select('', []));
})();
