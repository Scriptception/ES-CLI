#!/usr/bin/env python3
"""ES-CLI: A ncurses-based CLI tool for Elasticsearch."""
import sys
import urwid
import warnings
import urllib3
from config import Config
from es_client import ESClient
from ui import MainWindow

# Suppress SSL warnings globally
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='.*verify_certs=False.*')
warnings.filterwarnings('ignore', message='.*TLS.*insecure.*')
warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)

# Suppress urwid widget sizing warnings
warnings.filterwarnings('ignore', message='.*ColumnsWarning.*')
warnings.filterwarnings('ignore', message='.*Columns widget contents flags.*')
warnings.filterwarnings('ignore', message='.*BOX WEIGHT.*')
warnings.filterwarnings('ignore', message='.*Using fallback hardcoded.*')
warnings.filterwarnings('ignore', category=UserWarning, module='urwid')


def main():
    """Main entry point."""
    try:
        # Load configuration
        config = Config()
        
        # Initialize Elasticsearch client
        es_client = ESClient(config.elasticsearch_config)
        
        # Create main window
        main_window = MainWindow(es_client, config)
        
        # Set up palette
        palette = [
            ('header', 'black', 'light gray', 'standout'),
            ('row', 'light gray', 'black'),
            ('selected', 'white', 'dark blue', 'standout'),
            ('status', 'white', 'dark blue'),
            ('error', 'white', 'dark red'),
        ]
        
        # Create main loop handler
        def handle_unhandled_input(key):
            """Handle unhandled keyboard input."""
            if key == 'q':
                raise urwid.ExitMainLoop()
            elif key == 'n':
                # Next page
                if main_window.current_from + main_window.current_size < main_window.results_table.total_hits:
                    main_window.current_from += main_window.current_size
                    query, query_type = main_window.query_input.get_query()
                    if query:
                        main_window._on_query_submit(query, query_type)
            elif key == 'p':
                # Previous page
                if main_window.current_from > 0:
                    main_window.current_from = max(0, main_window.current_from - main_window.current_size)
                    query, query_type = main_window.query_input.get_query()
                    if query:
                        main_window._on_query_submit(query, query_type)
            elif key in ('right', 'l', 'left', 'h'):
                # Horizontal scrolling - let the results table handle it
                return None
        
        loop = urwid.MainLoop(
            main_window,
            palette=palette,
            unhandled_input=handle_unhandled_input
        )
        
        # Store loop reference in main_window for status updates
        main_window._main_loop = loop
        
        # Set focus on query input after UI is rendered
        def set_initial_focus(loop, user_data):
            try:
                main_window.focus_query_input()
            except Exception:
                pass
        
        # Use alarm to set focus after the first render (use 0 to set immediately after first draw)
        loop.set_alarm_in(0, set_initial_focus)
        
        # Run
        try:
            loop.run()
        except KeyboardInterrupt:
            # User pressed Ctrl+C, exit gracefully
            pass
        except urwid.ExitMainLoop:
            # Normal exit
            pass
        
    except FileNotFoundError as e:
        print(f"\nError: {e}", file=sys.stderr)
        print("\nPlease create a config.yaml file. See config.yaml.example for a template.", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        import traceback
        print(f"\nConfiguration Error: {e}", file=sys.stderr)
        if '--debug' in sys.argv:
            traceback.print_exc()
        sys.exit(1)
    except KeyboardInterrupt:
        # User pressed Ctrl+C during startup
        print("\n\nInterrupted by user.", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"\nError: {error_msg}", file=sys.stderr)
        # Always show traceback for decode errors to help debug
        if 'decode' in error_msg.lower() or "'dict' object has no attribute 'decode'" in error_msg:
            print("\nFull traceback:", file=sys.stderr)
            traceback.print_exc()
        elif '--debug' in sys.argv:
            print("\nFull traceback:", file=sys.stderr)
            traceback.print_exc()
        print("\nPress any key to exit...", file=sys.stderr)
        try:
            input()
        except:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()
