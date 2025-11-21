"""NCurses UI components for ES-CLI."""
import urwid
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, timedelta
import warnings
from time_range import TimeRange

# Suppress urwid widget sizing warnings
warnings.filterwarnings('ignore', message='.*ColumnsWarning.*')
warnings.filterwarnings('ignore', message='.*Columns widget contents flags.*')
warnings.filterwarnings('ignore', message='.*BOX WEIGHT.*')
warnings.filterwarnings('ignore', message='.*Using fallback hardcoded.*')
warnings.filterwarnings('ignore', category=UserWarning, module='urwid')


class TimeRangeSelector(urwid.WidgetWrap):
    """Time range selector widget."""
    
    def __init__(self, on_change: Optional[Callable[[str], None]] = None):
        """Initialize time range selector.
        
        Args:
            on_change: Optional callback when time range changes
        """
        self.on_change = on_change
        self.current_preset = TimeRange.DEFAULT_PRESET
        
        # Create buttons for each preset
        self.buttons = []
        for preset in TimeRange.PRESETS.keys():
            btn = urwid.Button(preset)
            urwid.connect_signal(btn, 'click', self._on_button_click)
            if preset == self.current_preset:
                btn.set_label(f"> {preset}")
            self.buttons.append(btn)
        
        # Create list box
        self.list_walker = urwid.SimpleFocusListWalker(self.buttons)
        self.listbox = urwid.ListBox(self.list_walker)
        
        # Info text
        self.info_text = urwid.Text(f"Time Range: {self.current_preset}", align='left')
        
        # Layout - use weight for listbox to allow flexible sizing
        self._widget = urwid.Pile([
            ('pack', self.info_text),
            ('weight', 1, self.listbox),
        ])
        
        super().__init__(self._widget)
    
    def _on_button_click(self, button):
        """Handle button click."""
        preset = button.get_label().replace('> ', '')
        self.set_preset(preset)
    
    def set_preset(self, preset: str):
        """Set the current preset.
        
        Args:
            preset: Preset name
        """
        if preset not in TimeRange.PRESETS:
            return
        
        self.current_preset = preset
        
        # Update button labels
        for btn in self.buttons:
            label = btn.get_label().replace('> ', '')
            if label == preset:
                btn.set_label(f"> {preset}")
            else:
                btn.set_label(label)
        
        # Update info text
        self.info_text.set_text(f"Time Range: {self.current_preset}")
        
        # Call callback
        if self.on_change:
            self.on_change(preset)
    
    def get_time_range(self) -> tuple[datetime, datetime]:
        """Get current time range.
        
        Returns:
            Tuple of (start_time, end_time)
        """
        return TimeRange.get_time_range(self.current_preset)


class QueryInput(urwid.WidgetWrap):
    """Query input widget with syntax selection."""
    
    def __init__(self, on_submit: Callable[[str, str], None]):
        """Initialize query input.
        
        Args:
            on_submit: Callback function(query_text, query_type)
        """
        self.on_submit = on_submit
        self.query_type = "ESQL"
        
        # Query type selector - use radio buttons group (ESQL is default)
        self.esql_radio = urwid.RadioButton([], "ESQL", state=True, on_state_change=self._on_type_change)
        self.kql_radio = urwid.RadioButton([self.esql_radio], "KQL", state=False, on_state_change=self._on_type_change)
        
        # Query input
        self.query_edit = urwid.Edit("Query: ", multiline=False, wrap='clip')
        urwid.connect_signal(self.query_edit, 'change', self._on_query_change)
        
        # Status text
        self.status_text = urwid.Text("Query type: ESQL", align='left')
        
        # Layout
        radio_group = urwid.Pile([
            self.esql_radio,
            self.kql_radio,
        ])
        header = urwid.Columns([
            ('weight', 1, urwid.Text("Query Type: ", align='right')),
            ('weight', 1, radio_group),
            ('weight', 2, urwid.Text("")),
        ])
        
        query_row = urwid.Columns([
            ('weight', 1, self.query_edit),
        ])
        
        self._widget = urwid.Pile([
            header,
            query_row,
            ('pack', self.status_text),
        ])
        
        super().__init__(self._widget)
    
    def _on_type_change(self, button, state):
        """Handle query type change."""
        if state:
            self.query_type = button.get_label()
            self.status_text.set_text(f"Query type: {self.query_type}")
    
    def _on_query_change(self, edit, text):
        """Handle query text change."""
        pass
    
    def keypress(self, size, key):
        """Handle keypress events."""
        if key == 'enter':
            query = self.query_edit.get_edit_text()
            if query.strip():
                # Get current query type from radio buttons
                if self.esql_radio.get_state():
                    query_type = "ESQL"
                else:
                    query_type = "KQL"
                self.on_submit(query.strip(), query_type)
        elif key == 'esc':
            self.query_edit.set_edit_text("")
        else:
            return super().keypress(size, key)
    
    def get_query(self) -> tuple[str, str]:
        """Get current query text and type."""
        # Check which radio button is selected
        if self.esql_radio.get_state():
            query_type = "ESQL"
        else:
            query_type = "KQL"
        return (self.query_edit.get_edit_text(), query_type)


class ResultsTable(urwid.WidgetWrap):
    """Table widget for displaying search results."""
    
    def __init__(self):
        """Initialize results table."""
        # Create list walker for rows
        self.list_walker = urwid.SimpleFocusListWalker([])
        self.listbox = urwid.ListBox(self.list_walker)
        
        # Info bar
        self.info_text = urwid.Text("No results", align='left')
        
        # Layout - listbox will handle scrolling naturally
        self._widget = urwid.Pile([
            ('pack', self.info_text),
            ('weight', 1, self.listbox),
        ])
        
        super().__init__(self._widget)
        
        # Track horizontal scroll position
        self._hscroll_pos = 0
        
        # Initialize attributes after super() to avoid property issues with urwid.WidgetWrap
        # Use _rows for internal storage, accessed via property
        object.__setattr__(self, 'headers', [])
        object.__setattr__(self, '_rows', [])
        object.__setattr__(self, 'current_row', 0)
        object.__setattr__(self, 'total_hits', 0)
        object.__setattr__(self, 'from_', 0)
        object.__setattr__(self, 'size', 100)
    
    def display_results(self, response: Dict[str, Any], query_type: str = "ESQL"):
        """Display search results.
        
        Args:
            response: Elasticsearch response
            query_type: Type of query (KQL or ESQL)
        """
        if query_type == "ESQL":
            self._display_esql_results(response)
        else:
            self._display_kql_results(response)
    
    def _display_kql_results(self, response: Dict[str, Any]):
        """Display KQL search results."""
        hits = response.get('hits', {}).get('hits', [])
        total = response.get('hits', {}).get('total', {})
        
        if isinstance(total, dict):
            self.total_hits = total.get('value', 0)
        else:
            self.total_hits = total
        
        if not hits:
            self.info_text.set_text("No results found")
            self.list_walker.clear()
            return
        
        # Extract headers from first hit
        if hits:
            first_hit = hits[0].get('_source', {})
            headers_list = list(first_hit.keys())
            
            # Add _id and _index if not present
            if '_id' not in headers_list:
                headers_list.insert(0, '_id')
            if '_index' not in headers_list:
                headers_list.insert(1, '_index')
            
            object.__setattr__(self, 'headers', headers_list)
        
        # Build rows - use object.__setattr__ to avoid property issues
        object.__setattr__(self, '_rows', [])
        for hit in hits:
            source = hit.get('_source', {})
            row = []
            
            # Add _id and _index
            row.append(str(hit.get('_id', '')))
            row.append(str(hit.get('_index', '')))
            
            # Add source fields
            for header in self.headers[2:]:
                value = source.get(header, '')
                # Format value
                if isinstance(value, (dict, list)):
                    value = str(value)
                elif isinstance(value, bool):
                    value = str(value)
                elif isinstance(value, (int, float)):
                    value = str(value)
                else:
                    value = str(value)
                row.append(value)
            
            # Append to rows list using property setter
            current_rows = getattr(self, '_rows', [])
            current_rows.append(row)
            object.__setattr__(self, '_rows', current_rows)
        
        # Filter out columns where all values are empty
        self._filter_empty_columns()
        
        # Reset horizontal scroll position after filtering
        self._hscroll_pos = 0
        
        # Update display
        self._update_display()
        
        # Update info
        start = self.from_ + 1
        end = min(self.from_ + len(hits), self.total_hits)
        headers = getattr(self, 'headers', [])
        scroll_info = ""
        max_cols_per_screen = 6
        if len(headers) > max_cols_per_screen:
            scroll_info = f" | Columns {self._hscroll_pos + 1}-{min(self._hscroll_pos + max_cols_per_screen, len(headers))} of {len(headers)} (←/→ to scroll)"
        self.info_text.set_text(
            f"Showing {start}-{end} of {self.total_hits} results{scroll_info} | "
            f"Press 'n' for next page, 'p' for previous, 'q' to quit"
        )
    
    def _display_esql_results(self, response: Dict[str, Any]):
        """Display ESQL query results."""
        columns = response.get('columns', [])
        values = response.get('values', [])
        
        if not columns or not values:
            self.info_text.set_text("No results found")
            self.list_walker.clear()
            return
        
        object.__setattr__(self, 'headers', [col.get('name', '') for col in columns])
        object.__setattr__(self, 'rows', [])
        
        rows_list = []
        for row_values in values:
            row = []
            for val in row_values:
                if isinstance(val, (dict, list)):
                    val = str(val)
                else:
                    val = str(val) if val is not None else ''
                row.append(val)
            rows_list.append(row)
        
        object.__setattr__(self, '_rows', rows_list)
        object.__setattr__(self, 'total_hits', len(rows_list))
        
        # Filter out columns where all values are empty
        self._filter_empty_columns()
        
        # Reset horizontal scroll position after filtering
        self._hscroll_pos = 0
        
        self._update_display()
        
        headers = getattr(self, 'headers', [])
        scroll_info = ""
        max_cols_per_screen = 6
        if len(headers) > max_cols_per_screen:
            scroll_info = f" | Columns {self._hscroll_pos + 1}-{min(self._hscroll_pos + max_cols_per_screen, len(headers))} of {len(headers)} (←/→ to scroll)"
        self.info_text.set_text(
            f"Showing {len(rows_list)} results{scroll_info} | "
            f"Press 'q' to quit"
        )
    
    def _filter_empty_columns(self):
        """Filter out columns where all values are empty."""
        rows = getattr(self, '_rows', [])
        headers = getattr(self, 'headers', [])
        
        if not headers or not rows:
            return
        
        # Find columns with all empty values
        empty_col_indices = set()
        for col_idx in range(len(headers)):
            all_empty = True
            for row in rows:
                if col_idx < len(row):
                    value = str(row[col_idx]).strip()
                    if value:  # Non-empty value found
                        all_empty = False
                        break
            if all_empty:
                empty_col_indices.add(col_idx)
        
        # Remove empty columns (in reverse order to maintain indices)
        # But keep at least one column if all are empty (to avoid breaking the display)
        if empty_col_indices and len(empty_col_indices) < len(headers):
            # Create new headers and rows without empty columns
            new_headers = [h for i, h in enumerate(headers) if i not in empty_col_indices]
            new_rows = []
            for row in rows:
                new_row = [val for i, val in enumerate(row) if i not in empty_col_indices]
                new_rows.append(new_row)
            
            object.__setattr__(self, 'headers', new_headers)
            object.__setattr__(self, '_rows', new_rows)
    
    def _calculate_column_widths(self, headers, rows, visible_start, visible_end):
        """Calculate optimal column widths based on content."""
        col_widths = []
        min_width = 15
        max_width = 100  # Increased to handle longer URLs and domain names
        
        for col_idx in range(visible_start, visible_end):
            if col_idx >= len(headers):
                break
            
            # Start with header width
            max_content_width = len(str(headers[col_idx]))
            
            # Check all rows for this column
            for row in rows:
                if col_idx < len(row):
                    content_len = len(str(row[col_idx]))
                    max_content_width = max(max_content_width, content_len)
            
            # Add padding (2 spaces on each side + 1 for divider)
            width = max_content_width + 3
            # Clamp between min and max
            width = max(min_width, min(width, max_width))
            col_widths.append(width)
        
        return col_widths
    
    def _update_display(self):
        """Update the listbox with current rows."""
        self.list_walker.clear()
        
        # Get rows safely
        rows = getattr(self, '_rows', [])
        headers = getattr(self, 'headers', [])
        
        if not headers or not rows:
            return
        
        # Calculate how many columns can fit (we'll use available width later)
        # For now, show columns starting from _hscroll_pos
        visible_start = self._hscroll_pos
        max_cols_per_screen = 6  # Reduced further to allow wider columns and prevent truncation
        
        # Determine visible columns
        visible_end = min(visible_start + max_cols_per_screen, len(headers))
        visible_headers = headers[visible_start:visible_end]
        
        # Calculate optimal column widths
        col_widths = self._calculate_column_widths(headers, rows, visible_start, visible_end)
        
        # Build header row
        header_cells = []
        # Add left scroll indicator
        if visible_start > 0:
            header_cells.append(('fixed', 3, urwid.Text("◄", align='center')))
        
        for i, h in enumerate(visible_headers):
            col_width = col_widths[i] if i < len(col_widths) else 30
            # Don't truncate header names - use full width
            header_text = f" {h:<{col_width-2}} "
            header_cells.append(('fixed', col_width, urwid.Text(header_text, align='left')))
        
        # Add right scroll indicator
        if visible_end < len(headers):
            header_cells.append(('fixed', 3, urwid.Text("►", align='center')))
        
        header_row = urwid.AttrMap(
            urwid.Columns(header_cells, dividechars=1),
            'header'
        )
        self.list_walker.append(header_row)
        
        # Add data rows
        for i, row in enumerate(rows):
            cells = []
            
            # Add left scroll indicator (spacer)
            if visible_start > 0:
                cells.append(('fixed', 3, urwid.Text(" ", align='center')))
            
            # Add visible columns
            for j in range(visible_start, min(visible_end, len(row))):
                col_idx = j - visible_start
                col_width = col_widths[col_idx] if col_idx < len(col_widths) else 30
                cell_str = str(row[j])
                
                # Only truncate if absolutely necessary (very long content)
                if len(cell_str) > col_width - 3:
                    # Truncate but show more content
                    cell_str = cell_str[:col_width-6] + "..."
                cell_text = f" {cell_str:<{col_width-2}} "
                cells.append(('fixed', col_width, urwid.Text(cell_text, align='left')))
            
            # Add right scroll indicator (spacer)
            if visible_end < len(headers):
                cells.append(('fixed', 3, urwid.Text(" ", align='center')))
            
            row_widget = urwid.AttrMap(
                urwid.Columns(cells, dividechars=1),
                'row',
                'selected'
            )
            self.list_walker.append(row_widget)
        
        # Set focus to first data row
        if len(self.list_walker) > 1:
            self.listbox.set_focus(1)
    
    def _update_info_text(self):
        """Update info text with current scroll position."""
        headers = getattr(self, 'headers', [])
        scroll_info = ""
        max_cols_per_screen = 6
        if len(headers) > max_cols_per_screen:
            scroll_info = f" | Columns {self._hscroll_pos + 1}-{min(self._hscroll_pos + max_cols_per_screen, len(headers))} of {len(headers)} (←/→ to scroll)"
        
        # Try to preserve existing info text content
        current_text = self.info_text.text
        # Extract the base message (before scroll info)
        if "Showing" in current_text:
            # For KQL results
            if "of" in current_text and "results" in current_text:
                parts = current_text.split(" | ")
                base_msg = parts[0] if parts else current_text
                self.info_text.set_text(f"{base_msg}{scroll_info} | Press 'n' for next page, 'p' for previous, 'q' to quit")
            else:
                # For ESQL results
                self.info_text.set_text(f"{current_text.split(' | ')[0]}{scroll_info} | Press 'q' to quit")
    
    def keypress(self, size, key):
        """Handle keypress events."""
        if key == 'q':
            return key
        elif key == 'n':
            # Next page - handled by parent
            return key
        elif key == 'p':
            # Previous page - handled by parent
            return key
        elif key == 'right' or key == 'l':
            # Scroll right
            headers = getattr(self, 'headers', [])
            max_cols_per_screen = 6
            max_scroll = max(0, len(headers) - max_cols_per_screen)
            if self._hscroll_pos < max_scroll:
                self._hscroll_pos += 1
                self._update_display()
                self._update_info_text()
            return None
        elif key == 'left' or key == 'h':
            # Scroll left
            if self._hscroll_pos > 0:
                self._hscroll_pos -= 1
                self._update_display()
                self._update_info_text()
            return None
        return super().keypress(size, key)
    
    def get_current_row(self) -> int:
        """Get currently focused row index."""
        focus = self.listbox.get_focus()
        if focus:
            return focus[1] - 1  # Subtract 1 for header
        return 0
    
    @property
    def rows(self):
        """Get rows list."""
        return getattr(self, '_rows', [])
    
    @rows.setter
    def rows(self, value):
        """Set rows list."""
        object.__setattr__(self, '_rows', value)


class MainWindow(urwid.WidgetWrap):
    """Main application window."""
    
    def __init__(self, es_client, config):
        """Initialize main window.
        
        Args:
            es_client: ESClient instance
            config: Config instance
        """
        self.es_client = es_client
        self.config = config
        self.current_index = config.default_index
        self.current_from = 0
        self.current_size = config.default_size
        
        # Create components
        self.query_input = QueryInput(self._on_query_submit)
        self.results_table = ResultsTable()
        self.time_range_selector = TimeRangeSelector()
        
        # Status bar - use a simple Text widget that handles FLOW sizing
        # Don't use wrap='clip' as it might cause issues, use 'space' instead
        self.status_bar_text = urwid.Text(
            f"Index: {self.current_index} | "
            f"Time Range: {TimeRange.DEFAULT_PRESET} | "
            f"Connected to Elasticsearch",
            align='left'
        )
        self.status_bar = urwid.AttrMap(self.status_bar_text, 'status')
        
        # Layout - stack query input and time range selector vertically to avoid sizing issues
        query_box = urwid.LineBox(self.query_input, title="Query")
        time_range_box = urwid.LineBox(self.time_range_selector, title="Time Range")
        
        # Put them side by side using Columns with proper sizing
        query_row = urwid.Columns([
            ('weight', 3, query_box),
            ('weight', 1, time_range_box),
        ], dividechars=1)
        
        # Use a simple Pile with pack for status bar - Text widget handles this correctly
        self._widget = urwid.Pile([
            ('pack', self.status_bar),  # Pack status bar - Text widget is FLOW
            (8, query_row),  # Fixed height for query section
            ('weight', 1, urwid.LineBox(self.results_table, title="Results")),
        ])
        
        super().__init__(self._widget)
        
        # Store reference to query_edit for focus management
        self._query_edit_widget = self.query_input.query_edit
        
        # Set up palette
        self.palette = [
            ('header', 'black', 'light gray', 'standout'),
            ('row', 'light gray', 'black'),
            ('selected', 'white', 'dark blue', 'standout'),
            ('status', 'white', 'dark blue'),
            ('error', 'white', 'dark red'),
        ]
    
    def focus_query_input(self):
        """Set focus on the query input field."""
        try:
            # Method 1: Navigate widget hierarchy step by step
            # Step 1: Focus on query_row in main Pile
            self._widget.set_focus(1)
            
            # Step 2: Get query_row and focus on query_box
            query_row = self._widget.contents[1][0]
            if hasattr(query_row, 'set_focus'):
                query_row.set_focus(0)
            
            # Step 3: Get query_box (LineBox) and its wrapped widget
            query_box_widget = query_row.contents[0][0]
            # For LineBox, we need to get the original_widget
            if hasattr(query_box_widget, 'original_widget'):
                query_input = query_box_widget.original_widget
            else:
                query_input = query_box_widget
            
            # Step 4: Focus on query_input's internal structure
            if hasattr(query_input, '_widget'):
                # Focus on query_row (index 1) inside QueryInput's Pile
                query_input._widget.set_focus(1)
                
                # Step 5: Get the query_row Columns widget inside QueryInput
                query_input_internal_row = query_input._widget.contents[1][0]
                if hasattr(query_input_internal_row, 'set_focus'):
                    # Focus on query_edit (index 0)
                    query_input_internal_row.set_focus(0)
        except Exception as e:
            # Fallback: Try simpler approach
            try:
                self._widget.set_focus(1)
            except Exception:
                pass
    
    def _on_query_submit(self, query: str, query_type: str):
        """Handle query submission.
        
        Args:
            query: Query text
            query_type: Query type (KQL or ESQL)
        """
        # Reset pagination for new queries
        self.current_from = 0
        
        # Show search in progress - update status bar immediately
        self.status_bar_text.set_text(f"⏳ Executing {query_type} query... Please wait (this may take a while)")
        self.status_bar.set_attr_map({None: 'status'})
        
        # Note: UI will freeze during search, but status message is set
        # The status bar will update when search completes
        
        self._search_in_progress = True
        self._search_cancelled = False
        
        try:
            # Get time range for both query types
            start_time, end_time = self.time_range_selector.get_time_range()
            
            # Execute query (this will block, but status is already shown)
            if query_type == "ESQL":
                # ESQL queries now also get time range filtering
                response = self.es_client.query_esql(
                    query,
                    time_range=(start_time, end_time)
                )
                self._search_in_progress = False
                self.results_table.display_results(response, query_type="ESQL")
                hits_count = getattr(self.results_table, 'total_hits', 0)
                time_range_str = self.time_range_selector.current_preset
                status_msg = f"✓ ESQL query executed successfully | Time Range: {time_range_str} | Results: {hits_count}"
            else:
                # Get time range
                start_time, end_time = self.time_range_selector.get_time_range()
                
                response = self.es_client.search_kql(
                    query,
                    index=self.current_index,
                    size=self.current_size,
                    from_=self.current_from,
                    time_range=(start_time, end_time)
                )
                self._search_in_progress = False
                self.results_table.display_results(response, query_type="KQL")
                time_range_str = self.time_range_selector.current_preset
                hits_count = getattr(self.results_table, 'total_hits', 0)
                status_msg = (
                    f"✓ KQL query executed successfully | "
                    f"Index: {self.current_index} | "
                    f"Time Range: {time_range_str} | "
                    f"Results: {hits_count}"
                )
            
            # Update status bar - urwid will redraw automatically
            self.status_bar_text.set_text(status_msg)
            self.status_bar.set_attr_map({None: 'status'})
                
        except ValueError as e:
            self._search_in_progress = False
            error_msg = str(e)
            # Truncate long error messages but keep them readable
            if len(error_msg) > 120:
                error_msg = error_msg[:117] + "..."
            self.status_bar_text.set_text(f"✗ Query error: {error_msg}")
            self.status_bar.set_attr_map({None: 'error'})
        except RuntimeError as e:
            self._search_in_progress = False
            error_msg = str(e)
            # Truncate long error messages but keep them readable
            if len(error_msg) > 120:
                error_msg = error_msg[:117] + "..."
            self.status_bar_text.set_text(f"✗ Error: {error_msg}")
            self.status_bar.set_attr_map({None: 'error'})
        except Exception as e:
            self._search_in_progress = False
            error_msg = str(e)
            # Truncate long error messages but keep them readable
            if len(error_msg) > 120:
                error_msg = error_msg[:117] + "..."
            self.status_bar_text.set_text(f"✗ Error: {error_msg}")
            self.status_bar.set_attr_map({None: 'error'})
    
    def keypress(self, size, key):
        """Handle keypress events - delegate to child widgets."""
        # Let child widgets handle their own keypresses
        return super().keypress(size, key)
