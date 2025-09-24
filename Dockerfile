FROM python:3.12-slim
WORKDIR /app
COPY app/ /app/app
COPY app/requirements.txt /app/app/requirements.txt
RUN pip install --no-cache-dir -r /app/app/requirements.txt

# Multi-sheet configuration - JSON format
# Format: [{"name": "Display Name", "sheet_id": "sheet_id", "tab": "tab_name"}, ...]
ENV SHEETS_CONFIG='[{"name": "Auto-QC", "sheet_id": "1KU9XnFkjdbROcpvmPztaXv9jC-62sLjA-2Mgb1N4_1o", "tab": "Github Actions"}, {"name": "Auto-Reviewer", "sheet_id": "1KU9XnFkjdbROcpvmPztaXv9jC-62sLjA-2Mgb1N4_1o", "tab": "Github Actions - Autoreview"}]'

# Legacy single sheet support (fallback)
ENV SHEET_ID=""
ENV SHEET_TAB="Sheet1"

# Other settings
ENV CACHE_TTL_SEC="60"
ENV PAGE_SIZE_DEFAULT="25"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
