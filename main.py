from os import makedirs;
from time import time_ns;
from sys import exit, stderr;
from typing import List, Dict;
from datetime import datetime;
from csv import reader, writer;
from serial import Serial, SerialException;
from statistics import median, quantiles, stdev;
from logging import basicConfig, INFO, FileHandler, StreamHandler, error, info, debug;

from utils import validate_sys;
from serial_port import init_serial;

# --- Configuration ---
LOG_DIR = "logs"
CSV_DIR = "data_logs" # Separate directory for CSV data
CSV_FILE_PREFIX = "csi_latency_data_"
STATS_FILE_PREFIX = "csi_latency_stats_"

# Use a timestamp for unique file names
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
CSV_FILENAME = f"{CSV_DIR}/{CSV_FILE_PREFIX}{TIMESTAMP}.csv"
STATS_FILENAME = f"{CSV_DIR}/{STATS_FILE_PREFIX}{TIMESTAMP}.csv"

# Ensure directories exist
makedirs(LOG_DIR, exist_ok=True)
makedirs(CSV_DIR, exist_ok=True)

basicConfig(
    level=INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        FileHandler(f"{LOG_DIR}/runtime_{TIMESTAMP}.log"), # Runtime logs to a separate file
        StreamHandler(stderr) # Console output for immediate feedback
    ]
)

def detect_firmware_type(line_content: str) -> (str, str|None):
    """Detects firmware type based on the first line."""
    if line_content.startswith("type,id,mac,rssi,rate,sig_mode,mcs,bandwidth,smoothing,not_sounding,aggregation,stbc,fec_coding,sgi,noise_floor,ampdu_cnt,channel,secondary_channel,local_timestamp,esp_epoch_us,ant,sig_len,rx_state,len,first_word,data"):
        return "Espressif CSI", "CSI_DATA"
    return "Unknown Firmware", None

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

def now_epoch_us() -> int:
	"""
	:return: Returns current epoch time in microseconds (int64).
	:rtype: int
	"""
	return (time_ns() // 1000);

def print_stats(deltas: List) -> None:
	print("\nFinal stats:")
	print(f" Median latency:	{median(deltas):.0f} micro second")
	print(f" Std dev: 				{stdev(deltas):.0f} micro second")
	print(f" Min / Max: 			{min(deltas)} / {max(deltas)} micro seconds")

def main() -> int:
	"""
	"""
	status: int
	usb_port: str
	configs: dict
	deltas: List[int] = []
	col_index: Dict[str, int] = {}
	data_indc: str;
	firmware_type: str = "Unknown Firmware"
	header_parsed: bool = False
	line_count: int = 0;
	MAX_LINES_BEFORE_HEADER_TIMEOUT: int = 500
	
	status, usb_port, configs = validate_sys()
	if (status < 0):
		return(1);
	BAUD_RATE = configs["baud_rate"]
	if not BAUD_RATE:
		error("missing baud rate in the config file")
		return (1);
	delta_file_handle, delta_csv_writer, stats_file_handle, stats_csv_writer = setup_csv_files()
	if not delta_file_handle:
		return (2);
	try:
		with Serial(usb_port, BAUD_RATE, timeout=10) as ser: #make timeout value part of json policy
			info(f"Serial port {usb_port} opened at {BAUD_RATE} baud.")
			info("Waiting for CSI data...")
			init_serial(ser)
			while (True):
				response: bytes = ser.readline()
				host_rx_epoch_us: int = now_epoch_us()
				if not response:
					debug("No response from serial port.")
					if line_count > MAX_LINES_BEFORE_HEADER_TIMEOUT and not header_parsed:
						error("Timeout waiting for header. Is the ESP connected and sending data?")
						break
					continue
				line_count += 1
				try:
					line: str = response.decode("utf-8", errors="replace")
				except Exception as e:
					error(f"Failed to decode response: {e} - raw: {response!r}")
					continue
				line: str = line.strip()
				if not line:
					debug("Received empty line.")
					continue
				if line.startswith("type,"):
					header: List = next(reader([line]))
					col_index = {name: i for i, name in enumerate(header)}
					if "esp_epoch_us" not in col_index:
						print("ERROR: Header missing required field esp_epoch_us", file=stderr)
						return (10);
					firmware_type, data_indc = detect_firmware_type(line)
					if "Unknown" not in firmware_type:
						header_parsed = True
					continue
				if header_parsed and line.startswith(data_indc):
					try:
						fields: List = next(reader([line]))
						esp_epoch_us = int(fields[col_index["esp_epoch_us"]])
					except (ValueError, IndexError, KeyError) as e:
						error(f"Parse error on CSI line: {e} | line: {line[:120]}")
						continue
					except Exception as e:
						error(f"Unexpected error parsing CSI line: {e} | line: {line[:120]}")
						continue
					delta_us: int = host_rx_epoch_us - esp_epoch_us
					deltas.append(delta_us)
					write_raw_delta(delta_csv_writer, host_rx_epoch_us, esp_epoch_us, delta_us)
					# if len(deltas) % 500 == 0:
					# 	med = median(deltas)
					# 	p90_val = int(quantiles(deltas, n=10)[8]) if len(deltas) >= 10 else "N/A"
					# 	p99_val = int(quantiles(deltas, n=100)[98]) if len(deltas) >= 99 else "N/A"
					if len(deltas) % 500 == 0:
						med = median(deltas)
						p90 = int(quantiles(deltas, n=10)[8])
						p99 = int(quantiles(deltas, n=100)[98])
						info(
								f"N={len(deltas):>6}  "
								f"median={med:>8.0f}μs  "
								f"p90={p90:>8}μs  "
								f"p99={p99:>8}μs  "
								f"last={delta_us:>8}μs"
						)
					if line_count > MAX_LINES_BEFORE_HEADER_TIMEOUT and not header_parsed and line.startswith(data_indc):
						logging.error("Received CSI data but header was not parsed within timeout. Possible issue with ESP data format or header transmission.")
						break
	except SerialException as e:
		print(f"{e}", file=stderr);
	except PermissionError:
		print("Permission denied - check user permissions", file=stderr);
	except UnicodeDecodeError as e:
		print(f"error while decoding: {e}", file=stderr);
	except KeyboardInterrupt:
		print("\nStopped by user.")
		exit(127);
	except Exception as e:
		print(f"Unexpected error: {e}", file=stderr);
	finally:
		# if deltas:
		# 	print_stats(deltas)
		if delta_file_handle:
			delta_file_handle.close()
		if stats_file_handle:
			write_final_stats_csv(stats_csv_writer, deltas, BAUD_RATE, firmware_type)
			stats_file_handle.close()
		if deltas:
			info(f"Collected {len(deltas)} samples.")
		else:
			info("No CSI data collected")
		info(f"Runtime log saved to: logs/runtime_{TIMESTAMP}.log")
		info(f"Raw data CSV saved to: {CSV_FILENAME}")
		info(f"Statistics CSV saved to: {STATS_FILENAME}")
	return (0);

if __name__ == "__main__":
	status = main();
	exit(status);
