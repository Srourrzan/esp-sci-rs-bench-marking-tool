from datetime import datetime;

# --- Configuration ---
LOG_DIR = "logs"
CSV_DIR = "data_logs" # Separate directory for CSV data
CSV_FILE_PREFIX = "csi_latency_data_"
STATS_FILE_PREFIX = "csi_latency_stats_"

# Use a timestamp for unique file names
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILENAME = f"{CSV_DIR}/{CSV_FILE_PREFIX}{TIMESTAMP}.csv"
STATS_FILENAME = f"{CSV_DIR}/{STATS_FILE_PREFIX}{TIMESTAMP}.csv"