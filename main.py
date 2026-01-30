import struct;
from sys import exit, stderr;
from serial import Serial, SerialException;
from time import perf_counter;
from json import load as jsload;
from json import JSONDecodeError;

from serial_port import find_port;

def load_config() -> (int, dict|None):
	try:
		with open("config.json", "r", encoding="utf-8") as file:
			config = jsload(file)
	except JSONDecodeError as e:
		print(f"Failed to decode JSON: {e}", file=stderr)
		return (-1, None);
	except FileNotFoundError as e:
		print(f"Config.json file was not found: {e}", file=stderr)
		return (-1, None);
	return (0, config);
    
def main():
	"""
	The timestamp coming from the esp-csi firmware, is coming from the Wi-Fi MAC hardware with microseconds resolution.
	It is being assigned in the Wi-Fi driver at the moment a packet is received by the Wi-Fi hardwarer (PHY+MAC)
	before it's passed up the stack.

	To record host_recieve_ts, I used `time.perf_counter()` where it can measure in nanoseconds, always increasing, does not go backwards.

	NEXT: I will calculate the clock offset via exchange protocol.
	"""
	usb_port: str;
	status: int;
	configs: dict;
	
	status, usb_port = find_port();
	if (status < 0):
		exit(1);
	status, configs = load_config()
	if (status < 0):
		exit(2);
	BAUD_RATE = configs["baud_rate"]
	while(True):
		try:
			with Serial(usb_port, BAUD_RATE) as ser:
				response: bytes = ser.readline();
				if not response:
					continue;
				host_receive_ts: float = perf_counter();
				print(f"receive_ts = {host_receive_ts}");
				line: str = response.decode("ascii", errors="ignore");
				fields: list = line.strip().split(',');
				print(f"fields =  {fields}");
				timestamp: int = int(fields[18]);
				print(f"timestamp: {timestamp}");
				esp_epoch_us: int = int(fields[19]);
				print(f"esp_epoch_us: {esp_epoch_us}")
				# break;
		except SerialException as e:
			print(f"{e}", file=stderr);
		except PermissionError:
			print("Permission denied - check user permissions", file=stderr);
		except UnicodeDecodeError as e:
			print(f"error while decoding: {e}", file=stderr);
		except KeyboardInterrupt:
			exit(127);
		except Exception as e:
			print(f"Unexpected error: {e}", file=stderr);
	return ;

if __name__ == "__main__":
	try:
		main();
	except SystemExit:
		print("exiting program");
	exit(0);
