import socket
import struct
import sys

# Configuration
AC_IP = "127.0.0.1"
AC_PORT = 9996

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2.0)

def start_telemetry():
    print(f"Connecting to {AC_IP}:{AC_PORT}...")
    
    # 1. Handshake (OpId 0)
    try:
        sock.sendto(struct.pack('<iii', 1, 1, 0), (AC_IP, AC_PORT))
        handshake_data, _ = sock.recvfrom(4096)
        
        # Decode Car Name from Handshake (Bytes 0-100 are Car Name in UTF-16)
        car_name = handshake_data[0:100].decode('utf-16', errors='ignore').split('%')[0]
        print(f"Connected! Car: {car_name}")
        
        # 2. Subscribe to Updates (OpId 1)
        sock.sendto(struct.pack('<iii', 1, 1, 1), (AC_IP, AC_PORT))
        
        print(f"{'Speed (kmh)':<12} | {'RPM':<8} | {'Gear':<5} | {'Gas':<5} | {'Brake':<5}")
        print("-" * 50)

        while True:
            data, _ = sock.recvfrom(4096)
            
            # Ensure we are processing the correct packet size
            if len(data) == 328:
                # --- Decoding Correct Offsets ---
                
                # Speed (Offset 8)
                speed = struct.unpack('<f', data[8:12])[0]
                
                # Gas (Offset 56)
                gas = struct.unpack('<f', data[56:60])[0]
                
                # Brake (Offset 60)
                brake = struct.unpack('<f', data[60:64])[0]
                
                # RPM (Offset 68)
                rpm = struct.unpack('<f', data[68:72])[0]
                
                # Gear (Offset 76)
                # AC UDP Gear logic: 1=Reverse, 2=Neutral, 3=1st Gear...
                raw_gear = struct.unpack('<i', data[76:80])[0]
                
                # Formatting Gear String
                if raw_gear == 0: gear_str = "R"
                elif raw_gear == 1: gear_str = "N"
                else: gear_str = str(raw_gear - 1)

                # Print
                print(f"{speed:12.1f} | {rpm:8.0f} | {gear_str:^5} | {gas:5.2f} | {brake:5.2f}", end='\r')

    except socket.timeout:
        print("\nNo data received. Are you on track?")
    except KeyboardInterrupt:
        print("\nDisconnecting...")
        sock.sendto(struct.pack('<iii', 1, 1, 3), (AC_IP, AC_PORT))
    finally:
        sock.close()

if __name__ == "__main__":
    start_telemetry()