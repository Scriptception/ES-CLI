# ES-CLI

A ncurses-based command-line interface for Elasticsearch, similar to Kibana but in your terminal.

## Features

- **Interactive Terminal UI**: Beautiful ncurses-based interface using urwid
- **Dual Query Support**: Execute both KQL (Kibana Query Language) and ESQL (Elasticsearch Query Language) queries
- **Tabular Results View**: Display search results in an interactive table format
- **Configuration File**: Easy setup with YAML configuration file
- **Pagination**: Navigate through large result sets with next/previous page controls
- **Real-time Query Execution**: Execute queries and see results instantly

## Installation

### Option 1: AppImage (Recommended for Linux)

Download the latest AppImage from the [Releases](https://github.com/yourusername/ES-CLI/releases) page:

```bash
# Download the AppImage
wget https://github.com/yourusername/ES-CLI/releases/latest/download/ES-CLI-x86_64.AppImage

# Make it executable
chmod +x ES-CLI-x86_64.AppImage

# Run it
./ES-CLI-x86_64.AppImage
```

The AppImage is a standalone executable that includes all dependencies - no installation required!

### Option 2: From Source

1. Clone this repository:
```bash
git clone <repository-url>
cd ES-CLI
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a configuration file:
```bash
cp config.yaml.example config.yaml
```

4. Edit `config.yaml` with your Elasticsearch connection details:
```yaml
elasticsearch:
  hosts:
    - http://localhost:9200
  # Optional: authentication
  # basic_auth:
  #   username: "elastic"
  #   password: "changeme"
  
default_index: "*"

query:
  default_size: 100
  max_size: 10000
```

## Usage

### Using AppImage:
```bash
./ES-CLI-x86_64.AppImage
```

### Using from source:
```bash
python main.py
```

Or make it executable:
```bash
chmod +x main.py
./main.py
```

### Keyboard Shortcuts

- **Enter**: Execute the current query
- **Esc**: Clear the query input
- **n**: Next page (for KQL queries)
- **p**: Previous page (for KQL queries)
- **q**: Quit the application
- **Arrow Keys**: Navigate through results

### Query Types

#### KQL (Kibana Query Language)
KQL queries are executed using Elasticsearch's query_string query. Examples:

```
status:200
response_time:>100
status:200 AND method:GET
host:web* AND (status:>=400 OR status:<200)
```

#### ESQL (Elasticsearch Query Language)
ESQL queries use Elasticsearch's ESQL API. Examples:

```
FROM logs | WHERE status > 200 | LIMIT 100
FROM logs-* | STATS avg(response_time) BY host
FROM logs | WHERE @timestamp > NOW() - 1d | LIMIT 1000
```

## Configuration

The configuration file (`config.yaml`) supports the following options:

- **elasticsearch.hosts**: List of Elasticsearch node URLs
- **elasticsearch.basic_auth**: Optional username/password for authentication
- **elasticsearch.use_ssl**: Enable SSL/TLS (optional)
- **elasticsearch.verify_certs**: Verify SSL certificates (optional)
- **elasticsearch.ca_certs**: Path to CA certificate file (optional)
- **default_index**: Default index pattern to search (default: "*")
- **query.default_size**: Default number of results per page (default: 100)
- **query.max_size**: Maximum number of results per page (default: 10000)

You can place the config file in:
- Current directory: `./config.yaml`
- Home directory: `~/.es-cli/config.yaml`

## Requirements

- Python 3.8+
- Elasticsearch 8.0+ (for ESQL support)
- Elasticsearch Python SDK 8.11.0+
- urwid 2.1.2+
- PyYAML 6.0+

## Building AppImage

To build an AppImage locally, see [BUILD.md](BUILD.md) for detailed instructions.

Quick build:
```bash
./build_appimage.sh
```

The AppImage will be created in `build/ES-CLI-x86_64.AppImage`.

## Architecture

- **main.py**: Entry point and application initialization
- **config.py**: Configuration file handling
- **es_client.py**: Elasticsearch client wrapper with KQL and ESQL support
- **ui.py**: NCurses UI components (query input, results table, main window)
- **build_appimage.sh**: Script to build AppImage
- **BUILD.md**: Detailed build instructions

## Limitations

- Charts/visualizations are not currently supported (tabular view only)
- ESQL pagination is limited (ESQL queries return all results at once)
- Results are displayed in a simplified table format (first 10 columns, 20 characters per cell)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License
