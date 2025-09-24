# Generalized Agents: Automated Quality Service Dashboard

A lightweight FastAPI application that transforms any Google Sheet into a searchable, paginated web interface. Perfect for sharing spreadsheet data without giving direct access to your Google Sheets.

## Features

- **Web Interface**: Clean, responsive HTML table with search and pagination
- **Multi-Sheet Support**: Configure and switch between multiple Google Sheets
- **Clickable Links**: Automatically detects and converts URLs to clickable links
- **Time-based Grouping**: Group data by day/week based on timestamp columns
- **REST API**: JSON endpoint for programmatic access to your sheet data
- **Real-time Search**: Filter rows across all columns with instant results
- **Pagination**: Configurable page sizes (10, 25, 50, 100 rows per page)
- **Caching**: Built-in TTL cache to minimize Google Sheets API calls
- **Docker Ready**: Containerized deployment with environment configuration
- **Service Account Auth**: Secure access using Google Cloud service accounts

## Endpoints

- `GET /` - Interactive web interface with search, pagination, and grouping controls
- `GET /api/data` - JSON API with query parameters:
  - `q` - Search term (searches across all columns)
  - `page` - Page number (default: 1)
  - `page_size` - Items per page (default: 25)
  - `group_by_period` - Group by time period: "day" or "week"
  - `timestamp_column` - Column name containing timestamps for grouping
- `GET /api/columns` - Get available columns and detected timestamp columns
- `GET /api/health` - Health check endpoint

### Time-based Grouping

The application can automatically group your data by time periods:

1. **Automatic Detection**: The system scans your sheet and identifies columns containing timestamps
2. **Flexible Formats**: Supports various timestamp formats including ISO 8601, common date formats
3. **Grouping Options**: 
   - **Day**: Groups records by calendar day and shows count per day
   - **Week**: Groups records by week (shows "Week of [date]") and shows count per week

**Example API calls**:
```bash
# Group by day using a timestamp column
GET /api/data?group_by_period=day&timestamp_column=created_at

# Group by week using a timestamp column
GET /api/data?group_by_period=week&timestamp_column=created_at
```

## Prerequisites

- Python 3.10+
- Google Cloud Service Account with Sheets API access
- Google Sheets API enabled in your GCP project
- Target sheet shared with service account email (Viewer permission sufficient)

## Quick Start

1. **Clone and setup environment**:
   ```bash
   git clone <repository-url>
   cd <repository-name>
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r app/requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your Google Sheet details
   ```

3. **Add service account credentials**:
   - Place your service account JSON file in the project root
   - Update `GOOGLE_APPLICATION_CREDENTIALS` in `.env` to point to the file

4. **Run the application**:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

5. **Access the interface**:
   - Web UI: http://127.0.0.1:8000
   - API: http://127.0.0.1:8000/api/data

## Configuration

Configure via `.env` file or environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SHEETS_CONFIG` | JSON array of sheet configurations (preferred) | See example |
| `SHEET_ID` | Google Sheet ID (legacy, fallback) | Required if no SHEETS_CONFIG |
| `SHEET_TAB` | Sheet tab/worksheet name (legacy) | `Sheet1` |
| `CACHE_TTL_SEC` | Cache duration in seconds | `60` |
| `PAGE_SIZE_DEFAULT` | Default pagination size | `25` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to service account JSON | Required |

Example `.env`:
```env
# Multi-sheet configuration (preferred)
SHEETS_CONFIG=[{"name": "Auto-QC", "sheet_id": "1KU9XnFkjdbROcpvmPztaXv9jC-62sLjA-2Mgb1N4_1o", "tab": "Sheet1"}, {"name": "Auto-Reviewer", "sheet_id": "1ABC123def456", "tab": "Reviews"}]

# Other settings
CACHE_TTL_SEC=60
PAGE_SIZE_DEFAULT=25
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
```

## Google Cloud Setup

1. **Create Service Account**:
   - Go to Google Cloud Console → IAM & Admin → Service Accounts
   - Create a new service account or use existing one
   - Generate and download JSON key

2. **Enable APIs**:
   - Enable Google Sheets API in your GCP project
   - No additional scopes needed beyond sheets readonly

3. **Share Sheet**:
   - Open your Google Sheet
   - Share with service account email: `SERVICE_ACCOUNT_NAME@PROJECT_ID.iam.gserviceaccount.com`
   - Grant "Viewer" permission (read-only access)

## Docker Deployment

**Build and run**:
```bash
docker build -t google-sheets-viewer .
docker run -p 8000:8000 \
  -e SHEETS_CONFIG='[{"name": "Auto-QC", "sheet_id": "your_sheet_id", "tab": "Sheet1"}]' \
  -e CACHE_TTL_SEC=60 \
  -e PAGE_SIZE_DEFAULT=25 \
  -e GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json \
  -v $(pwd)/service-account.json:/app/service-account.json:ro \
  google-sheets-viewer
```

**Using docker-compose** (recommended):
```yaml
version: '3.8'
services:
  sheets-viewer:
    build: .
    ports:
      - "8000:8000"
    environment:
      - SHEETS_CONFIG=[{"name": "Auto-QC", "sheet_id": "your_sheet_id", "tab": "Sheet1"}]
      - CACHE_TTL_SEC=60
      - PAGE_SIZE_DEFAULT=25
      - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
    volumes:
      - ./service-account.json:/app/service-account.json:ro
```

## Use Cases

- **Data Sharing**: Share spreadsheet data without giving direct Google Sheets access
- **Public Dashboards**: Create read-only views of internal data
- **API Integration**: Provide JSON endpoints for spreadsheet data
- **Quick Prototyping**: Rapidly deploy data interfaces without database setup

## Performance Notes

- **Caching**: Data is cached for the configured TTL to reduce API calls
- **Large Sheets**: For sheets with >10k rows, consider:
  - Reducing the range in `ws.get_all_records()`
  - Implementing server-side filtering
  - Migrating to BigQuery for better performance
- **Rate Limits**: Google Sheets API has quotas; adjust `CACHE_TTL_SEC` accordingly

## Security Considerations

- Service account JSON contains sensitive credentials - never commit to version control
- Use environment variables or secure secret management in production
- Consider IP restrictions and VPC deployment for sensitive data
- Current implementation is read-only; modify scopes carefully if adding write operations

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

