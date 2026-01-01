from serial.tools import list_ports;
from sys import stderr;

def find_port() -> (int, str):
    ports: list = list_ports.comports();
    port: str = None;
    
    for port_ in ports:
        if ((port_.description != "n/a") and ("/dev/ttyUSB" in port_.device or "COM" in port_.device)):
            print(f"{port_.device} is found");
            port = port_.device;
            break;
    if port is None:
        stderr.write("USB port not found\n");
        return (-1, port);
    return (0, port);

