import struct;
from sys import exit, stderr;
from serial.tools import list_ports;
from serial import Serial, SerialException;
from time import time, perf_counter;

from serial_port import find_port;

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
    
    status, usb_port = find_port();
    if (status < 0):
        exit(1);
    while(True):
        try:
            with Serial(usb_port, 921600) as ser:
                for i in range(4):
                    response: bytes = ser.readline();
                    host_receive_ts: float = perf_counter();
                    print(f"receive_ts {type(host_receive_ts)} = {host_receive_ts}");
                    print(f"response {type(response)} = {response}");
                    line: str = response.decode("ascii", errors="ignore");
                    fields: list = line.strip().split(',');
                    timestamp: int = int(fields[18]);
                    print(f"field =  {fields}");
                    print(f"timestamp: {timestamp}");
                    
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
        # finally:
        #     print(f"closing program");
        #     exit(2);
    return ;

if __name__ == "__main__":
    main();
    exit(0);
