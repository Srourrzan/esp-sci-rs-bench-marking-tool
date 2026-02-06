import subprocess;
from typing import Dict;
from sys import exit, stderr;
from serial_port import find_port;
from json import load, JSONDecodeError;


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

def check_ntp_sync() -> bool:
	"""
	:return: Returns True if the host system clock is 
	NTP-synchronized.
	:rtype: bool
	"""
	try:
		out = subprocess.check_output(["timedatectl"], text=True)
		return ("System clock synchronized: yes" in out);
	except Exception as e:
		print(f"Warning: couldn't verify NTP state: {e}", file=stderr)
		return (False);


def validate_sys() -> (int, str|None, Dict|None):
	"""
	Docstring for validate_sys
	
	:return: Description
	:rtype: Any
	"""
	usb_port: str
	configs: Dict

	if not check_ntp_sync():
		return (-1, None, None);
	status, usb_port = find_port()
	if (status < 0):
		return (-1, None, None);
	status, configs = load_config()
	if (status < 0):
		return (-1, None, None);
	return (0, usb_port, configs);