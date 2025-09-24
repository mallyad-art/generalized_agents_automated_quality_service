import os
import math
import re
import json
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import gspread
from google.oauth2.service_account import Credentials
from cachetools import TTLCache
from typing import Optional, Literal, Union, List, Dict

# Multi-sheet configuration
SHEETS_CONFIG_STR = os.environ.get("SHEETS_CONFIG", "")
SHEETS_CONFIG = []

# Legacy single sheet support
SHEET_ID = os.environ.get("SHEET_ID", "")
SHEET_TAB = os.environ.get("SHEET_TAB", "Sheet1")

# Parse multi-sheet configuration
if SHEETS_CONFIG_STR:
    try:
        SHEETS_CONFIG = json.loads(SHEETS_CONFIG_STR)
        print(f"Loaded {len(SHEETS_CONFIG)} sheet configurations")
    except json.JSONDecodeError as e:
        print(f"Error parsing SHEETS_CONFIG: {e}")
        SHEETS_CONFIG = []

# Fallback to single sheet if no multi-sheet config
if not SHEETS_CONFIG and SHEET_ID:
    SHEETS_CONFIG = [{"name": "Default Sheet", "sheet_id": SHEET_ID, "tab": SHEET_TAB}]
    print("Using legacy single sheet configuration")

if not SHEETS_CONFIG:
    raise RuntimeError("No sheet configuration found. Set SHEETS_CONFIG or legacy SHEET_ID environment variable.")

CACHE_TTL_SEC = int(os.environ.get("CACHE_TTL_SEC", "60"))  # refresh every 60s
PAGE_SIZE_DEFAULT = int(os.environ.get("PAGE_SIZE_DEFAULT", "25"))

# Auth with Service Account
creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
if not creds_path or not os.path.exists(creds_path):
    raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS is not set or file not found. "
                       "Point this to your service-account JSON key.")

scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
gc = gspread.authorize(creds)

app = FastAPI(title="Google Sheets Multi-Viewer")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# TTL cache for each sheet (maxsize per sheet)
cache = TTLCache(maxsize=len(SHEETS_CONFIG) * 2, ttl=CACHE_TTL_SEC)

def get_sheet_config(sheet_name: str) -> Dict:
    """Get sheet configuration by name"""
    for config in SHEETS_CONFIG:
        if config["name"] == sheet_name:
            return config
    raise ValueError(f"Sheet '{sheet_name}' not found in configuration")

def get_available_sheets() -> List[Dict]:
    """Get list of available sheets"""
    return [{"name": config["name"], "display_name": config["name"]} for config in SHEETS_CONFIG]

def is_url(text):
    """Check if text contains a URL"""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return bool(re.search(url_pattern, str(text)))

def make_links_clickable(text):
    """Convert URLs in text to clickable HTML links"""
    if pd.isna(text) or text == "":
        return text
    text_str = str(text)
    url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+)'
    return re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', text_str)

def highlight_search_term(text, search_term):
    """Highlight search term in text with HTML markup"""
    if pd.isna(text) or text == "" or not search_term or not search_term.strip():
        return str(text) if not pd.isna(text) else ""
    
    text_str = str(text)
    search_term_clean = search_term.strip()
    
    # Case-insensitive search and replace
    # Use word boundaries to avoid partial matches within HTML tags
    pattern = re.compile(re.escape(search_term_clean), re.IGNORECASE)
    highlighted = pattern.sub(
        lambda m: f'<mark style="background-color: #ffeb3b; padding: 1px 2px; border-radius: 2px;">{m.group()}</mark>',
        text_str
    )
    
    return highlighted

def process_cell_content(text, search_term=None):
    """Process cell content: make links clickable and highlight search terms"""
    if pd.isna(text) or text == "":
        return ""
    
    # First make links clickable
    processed = make_links_clickable(text)
    
    # Then highlight search terms (but avoid highlighting within HTML tags)
    if search_term and search_term.strip():
        # Only highlight if the text doesn't contain HTML tags (to avoid breaking link HTML)
        if '<a href=' not in processed:
            processed = highlight_search_term(processed, search_term)
        else:
            # For text with links, highlight only the text parts, not the URLs
            # This is a simple approach - we could make it more sophisticated
            text_parts = processed.split('<a href=')
            if len(text_parts) > 1:
                # Highlight only the first part (before any links)
                text_parts[0] = highlight_search_term(text_parts[0], search_term)
                processed = '<a href='.join(text_parts)
    
    return processed

def parse_timestamp(value):
    """Try to parse various timestamp formats"""
    if pd.isna(value) or value == "":
        return None
    
    try:
        # Try common formats
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%m/%d/%Y %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(str(value), fmt)
            except ValueError:
                continue
        
        # Try pandas parsing as fallback
        return pd.to_datetime(value)
    except:
        return None

def validate_timestamp_column(df, timestamp_col):
    """Validate that a column contains valid timestamp data"""
    if timestamp_col not in df.columns:
        return False, f"Column '{timestamp_col}' not found in the data"
    
    # Check if column exists and has data
    col_data = df[timestamp_col].dropna()
    if len(col_data) == 0:
        return False, f"Column '{timestamp_col}' contains no data"
    
    # Sample a reasonable number of values to check
    sample_size = min(50, len(col_data))
    sample_data = col_data.head(sample_size)
    
    # Count how many values can be parsed as timestamps
    valid_timestamps = 0
    for value in sample_data:
        if parse_timestamp(value) is not None:
            valid_timestamps += 1
    
    # Require at least 70% of sampled values to be valid timestamps
    valid_percentage = valid_timestamps / sample_size
    if valid_percentage < 0.7:
        return False, f"Column '{timestamp_col}' contains insufficient valid timestamp data ({valid_percentage:.1%} valid). Expected formats: YYYY-MM-DD, YYYY-MM-DD HH:MM:SS, ISO 8601, etc."
    
    return True, f"Column '{timestamp_col}' validated successfully ({valid_percentage:.1%} valid timestamps)"

def group_by_time_period(df, timestamp_col, period):
    """Group dataframe by time period with validation"""
    if timestamp_col not in df.columns:
        raise ValueError(f"Column '{timestamp_col}' not found in the data")
    
    # Validate timestamp column
    is_valid, message = validate_timestamp_column(df, timestamp_col)
    if not is_valid:
        raise ValueError(message)
    
    # Parse timestamps
    df = df.copy()
    df['_parsed_timestamp'] = df[timestamp_col].apply(parse_timestamp)
    
    # Filter out rows where timestamp couldn't be parsed
    original_count = len(df)
    df = df[df['_parsed_timestamp'].notna()]
    parsed_count = len(df)
    
    if parsed_count == 0:
        raise ValueError(f"No valid timestamps found in column '{timestamp_col}'")
    
    # Log how many rows were filtered out
    if parsed_count < original_count:
        print(f"Warning: {original_count - parsed_count} rows filtered out due to invalid timestamps")
    
    # Create grouping key based on period
    if period == 'day':
        df['_group_key'] = df['_parsed_timestamp'].dt.date
    elif period == 'week':
        df['_group_key'] = df['_parsed_timestamp'].dt.to_period('W').apply(lambda x: f"Week of {x.start_time.date()}")
    else:
        raise ValueError(f"Invalid period '{period}'. Must be 'day' or 'week'")
    
    # Group by time period only
    grouped = df.groupby('_group_key').agg({
        col: 'count' for col in df.columns if not col.startswith('_')
    }).reset_index()
    
    # Rename the group key column
    grouped = grouped.rename(columns={'_group_key': f'{period.title()}_Group'})
    
    return grouped

def load_sheet_df(sheet_name: str = None):
    """Load dataframe for a specific sheet"""
    # Default to first sheet if none specified
    if not sheet_name:
        sheet_name = SHEETS_CONFIG[0]["name"]
    
    cache_key = f"df_{sheet_name}"
    if cache_key in cache:
        return cache[cache_key]
    
    try:
        config = get_sheet_config(sheet_name)
        sh = gc.open_by_key(config["sheet_id"])
        ws = sh.worksheet(config["tab"])
        rows = ws.get_all_records()  # list[dict]; first row is headers in the sheet
        df = pd.DataFrame(rows)
        cache[cache_key] = df
        return df
    except Exception as e:
        raise ValueError(f"Error loading sheet '{sheet_name}': {str(e)}")

@app.get("/api/health")
def health():
    return {"ok": True, "sheets": len(SHEETS_CONFIG)}

@app.get("/api/sheets")
def get_sheets():
    """Get available sheets"""
    return JSONResponse({"sheets": get_available_sheets()})

@app.get("/api/data")
def api_data(
    q: Optional[str] = None, 
    page: int = 1, 
    page_size: int = PAGE_SIZE_DEFAULT,
    group_by_period: Optional[str] = None,
    timestamp_column: Optional[str] = None,
    sheet: Optional[str] = None
):
    # Load original data for specified sheet
    try:
        df = load_sheet_df(sheet)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    
    error_message = None
    grouped = False
    
    # Apply grouping if both parameters are provided and valid (grouping is optional)
    if group_by_period and group_by_period.strip() and timestamp_column and timestamp_column.strip():
        # Validate group_by_period value
        if group_by_period not in ["day", "week"]:
            error_message = f"Invalid grouping period '{group_by_period}'. Must be 'day' or 'week'"
        else:
            try:
                df = group_by_time_period(df, timestamp_column, group_by_period)
                grouped = True
            except ValueError as e:
                error_message = str(e)
                # Keep original data when grouping fails
                df = load_sheet_df(sheet)  # Reset to original data
    
    # Apply search filter (works on both grouped and ungrouped data)
    if q and q.strip():
        qlow = q.strip().lower()
        df = df[df.apply(lambda r: any(qlow in str(v).lower() for v in r), axis=1)]
    
    # Pagination
    total = len(df)
    start = max((page - 1) * page_size, 0)
    end = start + page_size
    page_df = df.iloc[start:end] if total else df
    
    # Process rows for API response (with highlighting if requested)
    rows = page_df.to_dict(orient="records")
    search_term = q.strip() if q and q.strip() else None
    if search_term:
        for row in rows:
            for col in row:
                if row[col] is not None:
                    row[col] = process_cell_content(row[col], search_term)
    
    response_data = {
        "total": int(total),
        "page": int(page),
        "page_size": int(page_size),
        "pages": int(math.ceil(total / page_size)) if page_size else 1,
        "rows": rows,
        "grouped": grouped,
        "search_term": search_term
    }
    
    if error_message:
        response_data["error"] = error_message
    
    return JSONResponse(response_data)

@app.get("/api/columns")
def get_columns(sheet: Optional[str] = None):
    """Get available columns for grouping"""
    try:
        df = load_sheet_df(sheet)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    
    columns = list(df.columns)
    
    # Try to identify timestamp columns
    timestamp_columns = []
    for col in columns:
        sample_values = df[col].dropna().head(5)
        if any(parse_timestamp(val) is not None for val in sample_values):
            timestamp_columns.append(col)
    
    return JSONResponse({
        "columns": columns,
        "timestamp_columns": timestamp_columns
    })

@app.get("/api/validate-timestamp")
def validate_timestamp_endpoint(column: str, sheet: Optional[str] = None):
    """Validate if a column contains valid timestamp data"""
    try:
        df = load_sheet_df(sheet)
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    
    is_valid, message = validate_timestamp_column(df, column)
    
    return JSONResponse({
        "valid": is_valid,
        "message": message,
        "column": column
    })

@app.get("/", response_class=HTMLResponse)
def index(
    request: Request, 
    q: Optional[str] = None, 
    page: int = 1, 
    page_size: int = PAGE_SIZE_DEFAULT,
    group_by_period: Optional[str] = None,
    timestamp_column: Optional[str] = None,
    sheet: Optional[str] = None
):
    # Load original data for specified sheet
    try:
        original_df = load_sheet_df(sheet)
    except ValueError as e:
        # If sheet loading fails, show error page
        return templates.TemplateResponse("error.html", {
            "request": request,
            "error": str(e),
            "available_sheets": get_available_sheets()
        })
    
    df = original_df.copy()
    current_sheet = sheet or SHEETS_CONFIG[0]["name"]
    
    # Get available columns and timestamp columns for the UI
    all_columns = list(original_df.columns)
    timestamp_columns = []
    for col in all_columns:
        sample_values = original_df[col].dropna().head(5)
        if any(parse_timestamp(val) is not None for val in sample_values):
            timestamp_columns.append(col)
    
    # Apply grouping if both parameters are provided and valid (grouping is optional)
    grouped = False
    error_message = None
    if group_by_period and group_by_period.strip() and timestamp_column and timestamp_column.strip():
        # Validate group_by_period value
        if group_by_period not in ["day", "week"]:
            error_message = f"Invalid grouping period '{group_by_period}'. Must be 'day' or 'week'"
        else:
            try:
                df = group_by_time_period(df, timestamp_column, group_by_period)
                grouped = True
            except ValueError as e:
                error_message = str(e)
                # Keep original data when grouping fails
                df = original_df.copy()
    
    # Apply search filter (works on both grouped and ungrouped data)
    if q and q.strip():
        qlow = q.strip().lower()
        df = df[df.apply(lambda r: any(qlow in str(v).lower() for v in r), axis=1)]
    
    # Pagination
    total = len(df)
    pages = int(math.ceil(total / page_size)) if page_size else 1
    start = max((page - 1) * page_size, 0)
    end = start + page_size
    page_df = df.iloc[start:end] if total else df
    
    cols = list(page_df.columns)
    rows = page_df.to_dict(orient="records")
    
    # Process cell content: make links clickable and highlight search terms
    search_term = q.strip() if q and q.strip() else None
    for row in rows:
        for col in cols:
            if row[col] is not None:
                row[col] = process_cell_content(row[col], search_term)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "q": q or "",
        "page": int(page),
        "pages": pages,
        "page_size": int(page_size),
        "cols": cols,
        "rows": rows,
        "total": int(total),
        "all_columns": all_columns,
        "timestamp_columns": timestamp_columns,
        "group_by_period": group_by_period or "",
        "timestamp_column": timestamp_column or "",
        "grouped": grouped,
        "error_message": error_message,
        "available_sheets": get_available_sheets(),
        "current_sheet": current_sheet
    })
