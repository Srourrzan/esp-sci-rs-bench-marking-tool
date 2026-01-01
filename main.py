import struct;
from sys import exit, stderr;
from serial.tools import list_ports;
from serial import Serial, SerialException;

from serial_port import find_port;

def main():
    usb_port: str;
    status: int;
    
    status, usb_port = find_port();
    if (status < 0):
        exit(1);
    try:
        with Serial(usb_port, 921600) as ser:
            while (True):
                response: bytes = ser.readline();
                values: int8 = struct.unpack(f"{len(response)}B", response);
                print(f"values: {values}");
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
    finally:
        print(f"closing program");
        exit(2);
    return ;

if __name__ == "__main__":
    main();
    exit(0);
