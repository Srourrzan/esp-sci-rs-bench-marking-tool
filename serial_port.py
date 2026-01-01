from serial.tools import list_ports;
from sys import stderr;

def find_port() -> (int, str):
    ports: list = list_ports.comports();
    
    for port_ in ports:
        if ((port_.description != "n/a") and (("/dev/ttyUSB" in port_.device) or ("COM" in port_.device))):
            print(f"{port_.device} is found");
            port = port_.device;
    if (port == None):
        stderr.write("USB port not found\n");
        return (-1, None);
    return (0, port);

