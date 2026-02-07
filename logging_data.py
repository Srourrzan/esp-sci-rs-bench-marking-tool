from csv import writer;
from typing import List;
from datetime import datetime;
from logging import error, info;
from statistics import median, quantiles, stdev;

from config import CSV_FILENAME, STATS_FILENAME;


def setup_csv_files():
    """Sets up CSV writers for raw deltas and final statistics."""
    try:
        # File for raw delta_us values
        delta_file = open(CSV_FILENAME, 'w', newline='', encoding='utf-8')
        delta_writer = writer(delta_file)
        delta_writer.writerow(['host_rx_epoch_us', 'esp_epoch_us', 'delta_us']) # Header for raw data
        # File for statistics
        stats_file = open(STATS_FILENAME, 'w', newline='', encoding='utf-8')
        stats_writer = writer(stats_file)
        # Header for stats - more detailed to capture context
        stats_writer.writerow([
            'timestamp',
            'baud_rate',
            'firmware_type',
            'total_samples',
            'median_us',
            'stdev_us',
            'min_us',
            'max_us',
            'p90_us', # Add percentile stats to CSV too
            'p99_us'
        ])
        return delta_file, delta_writer, stats_file, stats_writer
    except IOError as e:
        error(f"Failed to open CSV files: {e}")
        return None, None, None, None

def write_raw_delta(writer, host_ts_us: int, esp_ts_us: int, delta: int):
    """Writes a single delta_us measurement to the raw data CSV."""
    if writer:
        writer.writerow([host_ts_us, esp_ts_us, delta])

def write_final_stats_csv(writer, deltas: List, baud_rate: int, firmware_type: str):
	"""Writes the final calculated statistics to the stats CSV."""
	if not deltas or not writer:
		return
	median_val = median(deltas)
	stdev_val = stdev(deltas) if len(deltas) > 1 else 0
	min_val = min(deltas)
	max_val = max(deltas)
	p90_val = "N/A"
	p99_val = "N/A"

	try:
		if len(deltas) >= 10:
			q10 = quantiles(deltas, n=10)
			p90_val = int(q10[8]) if len(q10) > 8 else "N/A"
		if len(deltas) >= 99:
			q100 = quantiles(deltas, n=100)
			p99_val = int(q100[98]) if len(q100) > 98 else "N/A"		
		current_ts_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
		writer.writerow([
			current_ts_str,
			baud_rate,
			firmware_type,
			len(deltas),
			f"{median_val:.0f}",
			f"{stdev_val:.0f}",
			min_val,
			max_val,
			p90_val,
			p99_val
		])
		info("Final statistics written to CSV.")
	except Exception as e:
		error(f"Error writing final stats to CSV: {e}")
	return ;