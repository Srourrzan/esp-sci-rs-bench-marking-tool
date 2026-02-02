from csv import reader;
from sys import exit, stderr;
from typing import List, Dict;
from json import load, JSONDecodeError;
from serial import Serial, SerialException;
from time import perf_counter, time_ns, sleep;
from statistics import median, quantiles, stdev;

from serial_port import find_port, init_serial;

def load_config() -> (int, Dict|None):
	try:
		with open("config.json", "r", encoding="utf-8") as file:
			config: Dict = load(file)
	except JSONDecodeError as e:
		print(f"Failed to decode JSON: {e}", file=stderr)
		return (-1, None);
	except FileNotFoundError as e:
		print(f"Config.json file was not found: {e}", file=stderr)
		return (-1, None);
	return (0, config);

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

def validate_sys() -> (int, str|None, Dict|None):
	"""
	Docstring for validate_sys
	
	:return: Description
	:rtype: Any
	"""
	usb_port: str
	configs: Dict

	status, usb_port = find_port()
	if (status < 0):
		return (-1, None, None);
	status, configs = load_config()
	if (status < 0):
		return (-1, None, None);
	return (0, usb_port, configs);

def main() -> int:
	"""
	"""
	status: int
	usb_port: str
	configs: dict
	deltas: List[int] = []
	col_index: Dict[str, int] = {}
	
	status, usb_port, configs = validate_sys()
	if (status < 0):
		return(1);
	BAUD_RATE = configs["baud_rate"]
	try:
		with Serial(usb_port, BAUD_RATE, timeout=10) as ser: #make timeout value part of json policy
			init_serial(ser)
			while (True):
				response: bytes = ser.readline()
				host_rx_epoch_us = now_epoch_us()
				if not response:
					print(f"no response", file=stderr)
					continue;
				line: str = response.decode("utf-8", errors="strict")
				if not line:
					print(f"failed to decode line", file=stderr)
				line: str = line.strip()
				if line.startswith("type,"):
					reader_ = reader([line])
					header: List = next(reader_)
					col_index = {name: i for i, name in enumerate(header)}
					if "esp_epoch_us" not in col_index:
						print("ERROR: Header missing required field esp_epoch_us", file=stderr)
						return (10);
					continue
				if not line.startswith("CSI_DATA"):
					continue
				reader_ = reader([line])
				fields: List = next(reader_)
				try:
					esp_epoch_us = int(fields[col_index["esp_epoch_us"]])
				except (ValueError, IndexError) as e:
					print(f"Parse error: {e} | line: {line[:120]}")
					continue
				delta_us: int = host_rx_epoch_us - esp_epoch_us #vaive latency
				deltas.append(delta_us)
				if len(deltas) % 500 == 0:
					med = median(deltas)
					p90 = int(quantiles(deltas, n=10)[8])
					p99 = int(quantiles(deltas, n=100)[98])
					print(
							f"N={len(deltas):>6}  "
							f"median={med:>8.0f}μs  "
							f"p90={p90:>8}μs  "
							f"p99={p99:>8}μs  "
							f"last={delta_us:>8}μs"
					)
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
		if deltas:
			print_stats(deltas)
	return (0);

if __name__ == "__main__":
	status = main();
	exit(status);
