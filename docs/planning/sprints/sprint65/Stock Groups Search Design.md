### Revised UI Front-End Design

To facilitate the selection of one or more items from the `definition_groups` table in a stock market context (focusing on indexes, sectors, industries, and themes), the design emphasizes a streamlined, interactive table interface. This allows users to select rows via checkboxes or through a dynamic search mechanism that supports multi-selection by filtering based on keywords from the `name`, `type`, or `description` fields. 

Key features include:
- **Table Display**: A responsive table showing groups with columns for `name` (e.g., "S&P 500"), `type` (e.g., "index"), `description` (repeating the name as specified), `number_of_stocks` (derived count), and dummy columns: `avg_market_cap` (e.g., "$500B"), `ytd_performance` (e.g., "+12.5%"), `volatility` (e.g., "Medium"), and `last_updated` (from `last_update`).
- **Multi-Selection**: Checkboxes in the first column for selecting individual or multiple rows. Include a "Select All" checkbox in the header for bulk selection.
- **Dynamic Search and Filtering**: A prominent search bar at the top that filters table rows in real-time as users type keywords matching `name`, `type`, or `description`. This supports multi-selection by allowing users to filter, then check the desired rows. For enhanced usability, the search can highlight matching text within rows.
- **Type-Specific Multi-Select Filter**: Retained from the original design, a multi-select dropdown for `type` (e.g., "index", "sector", "theme") to narrow down options before or alongside keyword search.
- **Sorting**: Column headers enable ascending/descending sorting on all fields.
- **Actions**: Buttons below the table for "Confirm Selection" (to proceed with chosen groups) and "Cancel" or "Clear Selection".
- **Implementation**: Suggestion: To implement this interface in the Python-based single-page application TickStock, utilize Plotly Dash as the framework, leveraging the dash_table.DataTable component for the responsive table with native support for sorting, multi-row selection via checkboxes, and client-side filtering on small datasets (up to 300 rows). Integrate dynamic search and type-specific multi-select filtering through Dash callbacks, using Pandas for backend data preparation and aggregation from the PostgreSQL tables, ensuring real-time updates without server-side pagination for optimal performance.
- **Layout**: Compact for embedding as a modal, sidebar, or full page in a stock analysis application. Responsive design stacks columns on mobile devices.  Default layout will be DIV in page that can be collapsed to display results.
- **Accessibility**: Keyboard-navigable checkboxes and search, with ARIA roles for screen readers.
- **Visual Style**: Professional, with a clean grid layout, subtle row highlighting on hover/selection, and stock-market color cues (e.g., green for positive performance).

This design supports efficient multi-selection workflows, such as choosing multiple indexes or sectors for comparison or portfolio building, without unnecessary details.

### Wireframe Sketch

The following is a textual representation of a wireframe, using Markdown and ASCII art to depict the layout. 

```
+-------------------------------------------------------------+
| Header: Select Stock Market Groups                          |
| [Close Button X]                                            |
+-------------------------------------------------------------+
| Filters & Search:                                           |
| Type: [Multi-Select Dropdown: Index ▾ Sector ▾ Theme ▾]     |
| Search: [Dynamic Text Input: e.g., "S&P tech" ]             |
| (Filters rows by name, type, description; supports multi-select via checkboxes) |
+-------------------------------------------------------------+
| Groups Table (Sortable, Multi-Selectable)                   |
| +---------------+---------------+---------------+---------------+---------------+---------------+---------------+---------------+
| | Select      | Name          | Type          | Description   | Num Stocks    | Avg Mkt Cap   | YTD Perf      | Volatility    | Last Updated  |
| | (Chk All)   |               |               |               |               |               |               |               |              | ↑/↓
| +---------------+---------------+---------------+---------------+---------------+---------------+---------------+---------------+
| | [ ]         | S&P 500       | Index         | S&P 500       | 500           | $500B         | +12.5%        | Medium        | 2025-12-28   | ↑/↓
| | [ ]         | Technology    | Sector        | Technology    | 150           | $1T           | +18.2%        | High          | 2025-12-27   | ↑/↓
| | [ ]         | AI & Robotics | Theme         | AI & Robotics | 50            | $200B         | +25.0%        | High          | 2025-12-26   | ↑/↓
| | [ ]         | Healthcare    | Industry      | Healthcare    | 200           | $300B         | +8.7%         | Low           | 2025-12-25   | ↑/↓
| +---------------+---------------+---------------+---------------+---------------+---------------+---------------+---------------+
| Pagination: [1] [2] [3] ... [Next]  (Showing 1-4 of 100; Filtered by search) |
+-------------------------------------------------------------+
| Actions:                                                    |
| [Confirm Selection] [Clear Selection] [Cancel]              |
+-------------------------------------------------------------+
```

#### Key Wireframe Elements in Figma Terms
- **Frames**: Main modal frame with nested frames for Header, Filters/Search, Table, and Actions.
- **Components**:
  - Search Input: Text field with placeholder "Search by name, type, or description"; variant for "Filtered" state.
  - Table Row: Reusable with checkbox, text fields, and hover state (e.g., background #F0F0F0).
  - Multi-Select Dropdown: Component showing selected chips (e.g., "Index x", "Sector x").
- **Interactions**:
  - Type in Search → Swap to "Filtered Table" variant (simulate row reduction/highlighting).
  - Click Checkbox → Toggle "Selected" variant (e.g., blue background).
  - Click Column Header → Show sort arrow variants (asc/desc).
- **Styles**:
  - Typography: Inter font, 14px body, 16px headers.
  - Colors: #333 text, #FFF background; #4CAF50 accents for selected rows.
  - Borders: 1px #E0E0E0 for cells; rounded corners on modal (8px).
- **Variants**:
  - Table: "Full", "Filtered", "Sorted".
  - Actions Buttons: "Enabled" (after selection) vs. "Disabled".

This wireframe prioritizes intuitive selection, with the dynamic search enabling quick multi-item picks through filtering and checkbox interaction. If additional details like specific integrations or color schemes are provided, the design can be further refined.

### Copy web\templates\dashboard\market_overview.html calling it market_stock_selector.html so we can test the implementation.  Upon selection, display the details of the group in grid.  