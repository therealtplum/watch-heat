from __future__ import annotations
from jinja2 import Template
from pathlib import Path
from typing import List, Dict, Any

HTML_TMPL = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Watch Heat Report - {{ run_date }}</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
      margin: 0;
      padding: 20px;
      background: #f5f5f5;
      color: #333;
      line-height: 1.6;
    }
    .container {
      max-width: 1800px;
      margin: 0 auto;
      background: white;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      padding: 24px;
    }
    header {
      border-bottom: 2px solid #eee;
      padding-bottom: 16px;
      margin-bottom: 24px;
    }
    h1 {
      margin: 0 0 8px 0;
      color: #1a1a1a;
      font-size: 28px;
    }
    .meta {
      color: #666;
      font-size: 14px;
      margin-bottom: 16px;
    }
    .stats {
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
      margin-bottom: 24px;
      padding: 16px;
      background: #f9f9f9;
      border-radius: 6px;
    }
    .stat {
      flex: 1;
      min-width: 150px;
    }
    .stat-label {
      font-size: 12px;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }
    .stat-value {
      font-size: 24px;
      font-weight: 600;
      color: #1a1a1a;
    }
    .stat-value.hot { color: #d97706; }
    .controls {
      margin-bottom: 16px;
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      align-items: center;
    }
    .filter-input {
      padding: 8px 12px;
      border: 1px solid #ddd;
      border-radius: 4px;
      font-size: 14px;
      flex: 1;
      min-width: 200px;
    }
    .filter-toggle {
      padding: 8px 16px;
      border: 1px solid #ddd;
      border-radius: 4px;
      background: white;
      cursor: pointer;
      font-size: 14px;
      transition: all 0.2s;
    }
    .filter-toggle:hover {
      background: #f5f5f5;
    }
    .filter-toggle.active {
      background: #d97706;
      color: white;
      border-color: #d97706;
    }
    .table-wrapper {
      overflow-x: auto;
      margin-top: 16px;
    }
    table {
      border-collapse: collapse;
      width: 100%;
      font-size: 13px;
      min-width: 1200px;
    }
    th {
      background: #f8f8f8;
      text-align: left;
      padding: 12px 8px;
      font-weight: 600;
      color: #555;
      border-bottom: 2px solid #ddd;
      position: sticky;
      top: 0;
      z-index: 10;
      cursor: pointer;
      user-select: none;
      white-space: nowrap;
    }
    th:hover {
      background: #f0f0f0;
    }
    th.sort-asc::after {
      content: " ▲";
      font-size: 10px;
      opacity: 0.6;
    }
    th.sort-desc::after {
      content: " ▼";
      font-size: 10px;
      opacity: 0.6;
    }
    td {
      padding: 10px 8px;
      border-bottom: 1px solid #eee;
      white-space: nowrap;
    }
    tbody tr {
      transition: background 0.15s;
    }
    tbody tr:hover {
      background: #f9f9f9;
    }
    tbody tr.hot {
      background: #fff8e6;
    }
    tbody tr.hot:hover {
      background: #fff5d6;
    }
    .number {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .positive { color: #059669; font-weight: 500; }
    .negative { color: #dc2626; font-weight: 500; }
    .heat-high { background: #fef3c7; font-weight: 600; }
    .heat-medium { background: #fde68a; }
    .heat-low { background: #fef3c7; }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .badge-hot {
      background: #fef3c7;
      color: #92400e;
    }
    .empty {
      text-align: center;
      padding: 40px;
      color: #999;
    }
    @media (max-width: 768px) {
      .container { padding: 16px; }
      .stats { flex-direction: column; }
      .controls { flex-direction: column; }
      .filter-input { width: 100%; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>🔥 Watch Heat Report</h1>
      <div class="meta">Run Date: {{ run_date }} | Total Watches: {{ total_count }} | Hot Watches: {{ hot_count }}</div>
    </header>
    
    <div class="stats">
      <div class="stat">
        <div class="stat-label">Total Watches</div>
        <div class="stat-value">{{ total_count }}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Hot Watches</div>
        <div class="stat-value hot">{{ hot_count }}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Avg Heat Score</div>
        <div class="stat-value">{{ avg_heat }}</div>
      </div>
      <div class="stat">
        <div class="stat-label">Max Heat Score</div>
        <div class="stat-value">{{ max_heat }}</div>
      </div>
    </div>
    
    <div class="controls">
      <input type="text" class="filter-input" id="searchInput" placeholder="Search by brand, reference, or name...">
      <button class="filter-toggle active" id="showAll">All</button>
      <button class="filter-toggle" id="showHot">Hot Only</button>
    </div>
    
    <div class="table-wrapper">
      <table id="watchTable">
        <thead>
          <tr>
            <th data-sort="brand">Brand</th>
            <th data-sort="reference">Reference</th>
            <th data-sort="display_name">Name</th>
            <th data-sort="median_price" class="number">Price</th>
            <th data-sort="pct_7" class="number">Δ7d%</th>
            <th data-sort="pct_14" class="number">Δ14d%</th>
            <th data-sort="pct_30" class="number">Δ30d%</th>
            <th data-sort="z90" class="number">Z90</th>
            <th data-sort="dom_delta_14" class="number">DOM Δ14%</th>
            <th data-sort="supply_delta_14" class="number">Supply Δ14%</th>
            <th data-sort="ebay_mom_30" class="number">eBay Mom30</th>
            <th data-sort="heat" class="number">Heat</th>
            <th data-sort="max_bid_for_8pct" class="number">Max Bid (8%)</th>
            <th data-sort="max_bid_for_10pct" class="number">Max Bid (10%)</th>
          </tr>
        </thead>
        <tbody>
        {% for r in rows %}
          <tr class="{{ 'hot' if r.get('is_hot') else '' }}" data-hot="{{ 'true' if r.get('is_hot') else 'false' }}">
            <td>{{ r.get('brand', '') }}</td>
            <td><code>{{ r.get('reference', '') }}</code></td>
            <td>{{ r.get('display_name', '') }}</td>
            <td class="number">${{ '{:,.0f}'.format(r['median_price']) if r.get('median_price') not in (None, '') and r.get('median_price') != '' else '—' }}</td>
            <td class="number {{ 'positive' if r.get('pct_7', 0) not in (None, '') and r.get('pct_7', 0) > 0 else 'negative' if r.get('pct_7', 0) not in (None, '') and r.get('pct_7', 0) < 0 else '' }}">{{ '{:+.1f}'.format(r['pct_7']) if r.get('pct_7') not in (None, '') and r.get('pct_7') != '' else '—' }}</td>
            <td class="number {{ 'positive' if r.get('pct_14', 0) not in (None, '') and r.get('pct_14', 0) > 0 else 'negative' if r.get('pct_14', 0) not in (None, '') and r.get('pct_14', 0) < 0 else '' }}">{{ '{:+.1f}'.format(r['pct_14']) if r.get('pct_14') not in (None, '') and r.get('pct_14') != '' else '—' }}</td>
            <td class="number {{ 'positive' if r.get('pct_30', 0) not in (None, '') and r.get('pct_30', 0) > 0 else 'negative' if r.get('pct_30', 0) not in (None, '') and r.get('pct_30', 0) < 0 else '' }}">{{ '{:+.1f}'.format(r['pct_30']) if r.get('pct_30') not in (None, '') and r.get('pct_30') != '' else '—' }}</td>
            <td class="number">{{ '{:+.2f}'.format(r['z90']) if r.get('z90') not in (None, '') and r.get('z90') != '' else '—' }}</td>
            <td class="number {{ 'positive' if r.get('dom_delta_14', 0) not in (None, '') and r.get('dom_delta_14', 0) > 0 else 'negative' if r.get('dom_delta_14', 0) not in (None, '') and r.get('dom_delta_14', 0) < 0 else '' }}">{{ '{:+.1f}'.format(r['dom_delta_14']) if r.get('dom_delta_14') not in (None, '') and r.get('dom_delta_14') != '' else '—' }}</td>
            <td class="number {{ 'positive' if r.get('supply_delta_14', 0) not in (None, '') and r.get('supply_delta_14', 0) > 0 else 'negative' if r.get('supply_delta_14', 0) not in (None, '') and r.get('supply_delta_14', 0) < 0 else '' }}">{{ '{:+.1f}'.format(r['supply_delta_14']) if r.get('supply_delta_14') not in (None, '') and r.get('supply_delta_14') != '' else '—' }}</td>
            <td class="number">{{ '{:+.2f}'.format(r['ebay_mom_30']) if r.get('ebay_mom_30') not in (None, '') and r.get('ebay_mom_30') != '' else '—' }}</td>
            <td class="number heat-{{ 'high' if r.get('heat', 0) not in (None, '') and r.get('heat', 0) >= 0.75 else 'medium' if r.get('heat', 0) not in (None, '') and r.get('heat', 0) >= 0.5 else 'low' if r.get('heat', 0) not in (None, '') and r.get('heat', 0) > 0 else '' }}">{{ '{:+.2f}'.format(r['heat']) if r.get('heat') not in (None, '') and r.get('heat') != '' else '—' }}{% if r.get('is_hot') %} <span class="badge badge-hot">HOT</span>{% endif %}</td>
            <td class="number">${{ '{:,.0f}'.format(r['max_bid_for_8pct']) if r.get('max_bid_for_8pct') not in (None, '') and r.get('max_bid_for_8pct') != '' else '—' }}</td>
            <td class="number">${{ '{:,.0f}'.format(r['max_bid_for_10pct']) if r.get('max_bid_for_10pct') not in (None, '') and r.get('max_bid_for_10pct') != '' else '—' }}</td>
          </tr>
        {% endfor %}
        </tbody>
      </table>
    </div>
  </div>
  
  <script>
    const table = document.getElementById('watchTable');
    const tbody = table.querySelector('tbody');
    const searchInput = document.getElementById('searchInput');
    const showAll = document.getElementById('showAll');
    const showHot = document.getElementById('showHot');
    let currentSort = { column: null, direction: 'asc' };
    let allRows = Array.from(tbody.querySelectorAll('tr'));
    let filteredRows = allRows;
    
    // Search functionality
    function filterRows() {
      const query = searchInput.value.toLowerCase();
      const showHotOnly = showHot.classList.contains('active');
      
      filteredRows = allRows.filter(row => {
        const text = row.textContent.toLowerCase();
        const matchesSearch = !query || text.includes(query);
        const matchesFilter = !showHotOnly || row.dataset.hot === 'true';
        return matchesSearch && matchesFilter;
      });
      
      tbody.innerHTML = '';
      filteredRows.forEach(row => tbody.appendChild(row));
    }
    
    searchInput.addEventListener('input', filterRows);
    
    showAll.addEventListener('click', () => {
      showAll.classList.add('active');
      showHot.classList.remove('active');
      filterRows();
    });
    
    showHot.addEventListener('click', () => {
      showHot.classList.add('active');
      showAll.classList.remove('active');
      filterRows();
    });
    
    // Sorting functionality
    function parseValue(cell) {
      const text = cell.textContent.trim();
      if (text === '—' || text === '') return null;
      // Remove currency symbols and commas
      const cleaned = text.replace(/[$,]/g, '').replace(/[^\d.\-+]/g, '');
      const num = parseFloat(cleaned);
      return isNaN(num) ? text : num;
    }
    
    function sortTable(columnIndex) {
      const header = table.querySelectorAll('th')[columnIndex];
      const isNumeric = header.classList.contains('number');
      
      // Remove sort indicators
      table.querySelectorAll('th').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
      });
      
      // Determine sort direction
      if (currentSort.column === columnIndex) {
        currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
      } else {
        currentSort.column = columnIndex;
        currentSort.direction = 'asc';
      }
      
      // Sort rows
      const rows = Array.from(tbody.querySelectorAll('tr'));
      rows.sort((a, b) => {
        const aVal = parseValue(a.cells[columnIndex]);
        const bVal = parseValue(b.cells[columnIndex]);
        
        if (aVal === null && bVal === null) return 0;
        if (aVal === null) return 1;
        if (bVal === null) return -1;
        
        let comparison = 0;
        if (isNumeric) {
          comparison = aVal - bVal;
        } else {
          comparison = String(aVal).localeCompare(String(bVal));
        }
        
        return currentSort.direction === 'asc' ? comparison : -comparison;
      });
      
      // Re-append sorted rows
      rows.forEach(row => tbody.appendChild(row));
      
      // Add sort indicator
      header.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
    }
    
    // Add click handlers to headers
    table.querySelectorAll('th').forEach((th, index) => {
      th.addEventListener('click', () => sortTable(index));
    });
  </script>
</body>
</html>
"""

def render_html(rows: List[Dict[str, Any]], out_path: Path, run_date: str) -> None:
    """Render HTML report from watch data.
    
    Args:
        rows: List of dictionaries containing watch data
        out_path: Path to save HTML file
        run_date: Date string for the report
    """
    if not rows:
        raise ValueError("No rows to render")
    
    # Calculate statistics
    total_count = len(rows)
    hot_count = sum(1 for r in rows if r.get('is_hot'))
    
    heat_values = [float(r.get('heat', 0)) for r in rows if r.get('heat') not in (None, '', '') and str(r.get('heat', '')).strip()]
    avg_heat = f"{sum(heat_values) / len(heat_values):.2f}" if heat_values else "0.00"
    max_heat = f"{max(heat_values):.2f}" if heat_values else "0.00"
    
    html = Template(HTML_TMPL).render(
        rows=rows,
        run_date=run_date,
        total_count=total_count,
        hot_count=hot_count,
        avg_heat=avg_heat,
        max_heat=max_heat
    )
    Path(out_path).write_text(html, encoding="utf-8")
