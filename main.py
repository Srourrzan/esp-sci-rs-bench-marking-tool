from serial.tools import list_ports;
from serial import Serial, SerialException;
from sys import exit, stderr;

from serial_port import find_port;

def main():
    usb_port: str;
    status: int;
    status, usb_port = find_port();
    if (status < 0):
        exit(1);
    ser: Serial = Serial(usb_port, 921600);
    try:
        while(1):
            response: str = ser.readline();
            print(f"response {type(response)}=\n{response.decode("utf-8").strip()}");
    except SerialException as e:
        print(f"{e}", file=stderr);
    return ;

if __name__ == "__main__":
    main();
    exit(0);
