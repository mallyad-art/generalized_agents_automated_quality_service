# Google Sheets Web Viewer

A lightweight FastAPI application that transforms any Google Sheet into a searchable, paginated web interface. Perfect for sharing spreadsheet data without giving direct access to your Google Sheets.

## Features

- **Web Interface**: Clean, responsive HTML table with search and pagination
- **Multi-Sheet Support**: Configure and switch between multiple Google Sheets
- **Timestamp Sorting**: Sort data by timestamp columns with ascending/descending options
- **Deduplication**: Remove duplicate runs, keeping latest by timestamp per unique key
- **Clickable Links**: Automatically detects and converts URLs to clickable links
- **Column Transforms**: Transform column values using templates (e.g., add prefixes/suffixes)
- **Day Filtering (Optional)**: Filter data by specific time periods (today, yesterday, past 7 days)
- **Time-based Grouping**: Group data by day/week based on timestamp columns
- **REST API**: JSON endpoint for programmatic access to your sheet data
- **Real-time Search**: Filter rows across all columns with instant results
- **Pagination**: Configurable page sizes (10, 25, 50, 100 rows per page)
- **Caching**: Built-in TTL cache to minimize Google Sheets API calls
- **Docker Ready**: Containerized deployment with environment configuration
- **Service Account Auth**: Secure access using Google Cloud service accounts

## Architecture

### High-Level System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│                 │    │                  │    │                     │
│   Web Browser   │◄──►│   FastAPI App    │◄──►│   Google Sheets     │
│                 │    │                  │    │                     │
│  - HTML UI      │    │  - Web Routes    │    │  - Auto-QC Data     │
│  - Search       │    │  - API Routes    │    │  - Auto-Reviewer    │
│  - Pagination   │    │  - Data Processing│   │  - Service Account  │
│  - Deduplication│    │  - Caching       │    │    Authentication   │
│                 │    │                  │    │                     │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │                  │
                       │   Static Files   │
                       │                  │
                       │  - Logo/Assets   │
                       │  - CSS Styles    │
                       │                  │
                       └──────────────────┘
```

### Data Processing Pipeline

```
Google Sheets Data
        │
        ▼
┌─────────────────┐
│  Load & Cache   │ ◄── TTL Cache (60s default)
│   Raw Data      │
└─────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│  Deduplication  │────►│  Keep Latest by  │
│   (Optional)    │     │   Timestamp      │
└─────────────────┘     └──────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│  Time Grouping  │────►│  Group by Day/   │
│   (Optional)    │     │     Week         │
└─────────────────┘     └──────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│ Timestamp Sort  │────►│ Sort by Timestamp│
│   (Optional)    │     │  (Desc/Asc)      │
└─────────────────┘     └──────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│  Search Filter  │────►│  Text Matching   │
│   (Optional)    │     │  & Highlighting  │
└─────────────────┘     └──────────────────┘
        │
        ▼
┌─────────────────┐     ┌──────────────────┐
│   Pagination    │────►│  Page Slicing    │
│                 │     │  & Navigation    │
└─────────────────┘     └──────────────────┘
        │
        ▼
┌─────────────────┐
│  HTML/JSON      │
│   Response      │
└─────────────────┘
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI Application                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │   Web Routes    │  │   API Routes    │  │  Static Files   │ │
│  │                 │  │                 │  │                 │ │
│  │  GET /          │  │  GET /api/data  │  │  GET /static/*  │ │
│  │  - HTML UI      │  │  - JSON Data    │  │  - Logo         │ │
│  │  - Templates    │  │  - Pagination   │  │  - CSS          │ │
│  │  - Forms        │  │  - Search       │  │                 │ │
│  │                 │  │                 │  │                 │ │
│  │                 │  │  GET /api/      │  │                 │ │
│  │                 │  │  - sheets       │  │                 │ │
│  │                 │  │  - columns      │  │                 │ │
│  │                 │  │  - validate     │  │                 │ │
│  │                 │  │  - deduplicate  │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                      Data Processing Layer                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │  Sheet Loader   │  │  Data Processor │  │  Cache Manager  │ │
│  │                 │  │                 │  │                 │ │
│  │  - Multi-sheet  │  │  - Deduplication│  │  - TTL Cache    │ │
│  │    support      │  │  - Time grouping│  │  - Per-sheet    │ │
│  │  - gspread      │  │  - Timestamp    │  │    caching      │ │
│  │    integration  │  │    sorting      │  │  - Auto-refresh │ │
│  │  - Error        │  │  - Search filter│  │                 │ │
│  │    handling     │  │  - Pagination   │  │                 │ │
│  │                 │  │  - Link         │  │                 │ │
│  │                 │  │    detection    │  │                 │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    Google Sheets Integration                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐ │
│  │ Service Account │  │  Sheets API     │  │  Data Formats   │ │
│  │                 │  │                 │  │                 │ │
│  │  - JSON Key     │  │  - Read-only    │  │  - Auto-QC      │ │
│  │  - OAuth Scopes │  │    access       │  │  - Auto-Reviewer│ │
│  │  - Secure Auth  │  │  - Multiple     │  │  - Timestamps   │ │
│  │                 │  │    sheets       │  │  - URLs         │ │
│  │                 │  │  - Rate limits  │  │  - Mixed data   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Scenarios

#### Scenario 1: Individual Runs View (Default)
```
User Request → Load Sheet → Apply Sorting → Apply Search → Paginate → Display
                    │              │
                    ▼              ▼
            "All Individual Execution Runs"    Sort by timestamp
            Each row = separate Auto-QC/Auto-Reviewer run    (desc/asc)
```

#### Scenario 2: Distinct Records View (Deduplicated)
```
User Request → Load Sheet → Deduplicate by Key → Keep Latest by Timestamp → Apply Sorting → Apply Search → Paginate → Display
                                    │                        │                     │
                                    ▼                        ▼                     ▼
                            Group by unique field    Sort by timestamp (desc)    Sort final results
                            (e.g., user_id)         Keep first occurrence       by timestamp (desc/asc)
                                    │                        │                     │
                                    ▼                        ▼                     ▼
                            "Distinct Records (Latest Run Per Key)"
                            Each row = latest run per unique identifier
```

#### Scenario 3: Time-based Grouping
```
User Request → Load Sheet → Group by Time Period → Aggregate Counts → Apply Sorting → Display Summary
                                    │                      │                │
                                    ▼                      ▼                ▼
                            Parse timestamps        Count records per    Sort time periods
                            Group by day/week       time period         chronologically (desc/asc)
                                    │                      │                │
                                    ▼                      ▼                ▼
                            "Grouped Data Summary"
                            Each row = time period with counts
```

#### Scenario 4: Sorting Only
```
User Request → Load Sheet → Validate Timestamp Column → Apply Sorting → Apply Search → Paginate → Display
                                    │                         │
                                    ▼                         ▼
                            Check column contains        Sort by parsed timestamps
                            valid timestamp data         (newest/oldest first)
                                    │                         │
                                    ▼                         ▼
                            "Sorted View: Data sorted by [column] timestamp"
                            Rows ordered chronologically by selected timestamp
```

## Endpoints

- `GET /` - Interactive web interface with search, pagination, deduplication, and grouping controls
- `GET /api/data` - JSON API with query parameters:
  - `q` - Search term (searches across all columns)
  - `page` - Page number (default: 1)
  - `page_size` - Items per page (default: 25)
  - `sort_column` - Timestamp column name for sorting
  - `sort_order` - Sort direction: "desc" (newest first, default) or "asc" (oldest first)
  - `group_by_period` - Group by time period: "day" or "week"
  - `timestamp_column` - Column name containing timestamps for operations
  - `day_filter` - (Optional) Filter by time period: "today", "yesterday", "past_7"
  - `dedupe_field` - Field to deduplicate by (e.g., "user_id", "email")
  - `dedupe_timestamp` - Timestamp field to determine latest record
- `GET /api/deduplicate` - Dedicated deduplication endpoint with same parameters as `/api/data` plus `sort_order`
- `GET /api/columns` - Get available columns and detected timestamp columns
- `GET /api/validate-timestamp` - Validate if a column contains valid timestamp data

- `GET /api/sheets` - Get list of available sheets
- `GET /api/health` - Health check endpoint

### Data Deduplication

Transform your view from "all individual runs" to "distinct records" by removing duplicates:

1. **Unique Key Selection**: Choose any field to deduplicate by (e.g., user_id, email, task_id)
2. **Latest Record Logic**: Automatically keeps the most recent run based on timestamp
3. **Duplicate Removal**: Shows exactly how many duplicate runs were filtered out
4. **Flexible Timestamps**: Supports various timestamp formats for "latest" determination

**Use Cases**:
- **Auto-QC Results**: Show latest quality check per user/task instead of all runs
- **Auto-Reviewer Data**: Display most recent review per item, hiding older attempts
- **Status Tracking**: Get current state by removing historical duplicate entries

**Example API calls**:
```bash
# Show distinct users, keeping their latest Auto-QC run
GET /api/data?dedupe_field=user_id&dedupe_timestamp=created_at

# Deduplicate by email, keeping latest by updated timestamp
GET /api/deduplicate?dedupe_field=email&dedupe_timestamp=last_updated

# Combine deduplication with search
GET /api/data?dedupe_field=task_id&dedupe_timestamp=completed_at&q=passed

# Combine day filtering with deduplication
GET /api/data?dedupe_field=user_id&dedupe_timestamp=created_at&day_filter=today&timestamp_column=created_at
```

### Day Filtering (Optional)
Optionally filter your data to show only records from specific time periods based on timestamp values:

```bash
# Show only today's records (since midnight)
GET /api/data?timestamp_column=created_at&day_filter=today

# Show only yesterday's records  
GET /api/data?timestamp_column=created_at&day_filter=yesterday

# Show records from the past 7 days (including today)
GET /api/data?timestamp_column=created_at&day_filter=past_7
```

**Available Time Filters:**
- `today` - Records from today only (since midnight)
- `yesterday` - Records from yesterday only
- `past_7` - Records from the past 7 days (including today)

**What it does:**
- Filters records based on timestamp values in the selected column
- Shows only records that fall within the specified time period
- Combines with search, deduplication, and grouping features
- Uses server timezone for consistent filtering
- Gracefully handles invalid or missing timestamps

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

# Combine deduplication with grouping
GET /api/data?dedupe_field=user_id&dedupe_timestamp=created_at&group_by_period=day&timestamp_column=created_at

# Combine day filtering with grouping (show past 7 days grouped by day)
GET /api/data?day_filter=past_7&group_by_period=day&timestamp_column=created_at
```

### Timestamp Sorting

Sort your data by timestamp columns with flexible ordering options:

1. **Automatic Detection**: The system identifies timestamp columns in your sheet
2. **Default Descending**: Always defaults to newest-first (descending) order
3. **User Choice**: Users can switch to oldest-first (ascending) order
4. **Universal Support**: Works across all views:
   - **Individual Runs**: Direct sorting of all records
   - **Deduplication**: Sorts deduplicated results by timestamp
   - **Grouping**: Sorts grouped time periods chronologically

**Key Features**:
- **Timestamp-Only**: Only allows sorting by validated timestamp columns
- **Format Flexible**: Supports various timestamp formats (ISO 8601, common date formats)
- **Real-time Validation**: Client-side validation ensures selected columns contain valid timestamps
- **Parameter Persistence**: Sorting preferences preserved across navigation and operations

**Example API calls**:
```bash
# Sort by timestamp, newest first (default)
GET /api/data?sort_column=created_at&sort_order=desc

# Sort by timestamp, oldest first
GET /api/data?sort_column=updated_at&sort_order=asc

# Combine sorting with deduplication (sorts deduplicated results)
GET /api/data?dedupe_field=user_id&dedupe_timestamp=created_at&sort_column=created_at&sort_order=desc

# Combine sorting with grouping (sorts grouped time periods)
GET /api/data?group_by_period=day&timestamp_column=created_at&sort_column=created_at&sort_order=asc

# Sort with search and pagination
GET /api/data?sort_column=completed_at&sort_order=desc&q=success&page=2&page_size=50
```

**UI Controls**:
- **Sort Column Dropdown**: Select from detected timestamp columns
- **Sort Order Dropdown**: Choose "Newest First (Descending)" or "Oldest First (Ascending)"
- **Apply/Clear Buttons**: Apply sorting or clear to return to default order
- **Status Display**: Shows current sorting status in the interface



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
