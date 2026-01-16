import socket
import struct
import sys
import os

# Configuration
AC_IP = "127.0.0.1"
AC_PORT = 9996

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(2.0)

def get_gear_char(raw_gear):
    # 0=R, 1=N, 2=1st...
    if raw_gear == 0: return "R"
    elif raw_gear == 1: return "N"
    else: return str(raw_gear - 1)

def start_telemetry():
    print(f"Connecting to {AC_IP}:{AC_PORT}...")
    try:
        # 1. Handshake
        sock.sendto(struct.pack('<iii', 1, 1, 0), (AC_IP, AC_PORT))
        handshake_data, _ = sock.recvfrom(4096)
        car_name = handshake_data[0:100].decode('utf-16', errors='ignore').split('%')[0]
        
        # 2. Subscribe to Update (Physics) AND Spot (Lap) events
        sock.sendto(struct.pack('<iii', 1, 1, 1), (AC_IP, AC_PORT)) # Subscribe Update
        sock.sendto(struct.pack('<iii', 1, 1, 2), (AC_IP, AC_PORT)) # Subscribe Spot
        
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

        while True:
            data, _ = sock.recvfrom(4096)
            
            # --- PACKET TYPE 1: PHYSICS (328 Bytes) ---
            if len(data) == 328:
                # Speed (Offset 8)
                speed = struct.unpack('<f', data[8:12])[0]
                
                # G-Forces (Vectors are usually Offsets 24-36)
                # Mapping: 24=X(Lat), 28=Y(Vert), 32=Z(Long)
                g_lat = struct.unpack('<f', data[24:28])[0]
                g_vert = struct.unpack('<f', data[28:32])[0]
                g_long = struct.unpack('<f', data[32:36])[0]

                # Inputs
                gas = struct.unpack('<f', data[56:60])[0]
                brake = struct.unpack('<f', data[60:64])[0]
                
                # Clutch (Offset 64) - Inverted Logic
                raw_clutch = struct.unpack('<f', data[64:68])[0]
                clutch = 1.0 - raw_clutch
                
                # RPM (Offset 68)
                rpm = struct.unpack('<f', data[68:72])[0]
                
                # Steer (Offset 72) - Previously mistaken for Max RPM
                steer = struct.unpack('<f', data[72:76])[0]
                
                # Gear (Offset 76)
                gear = struct.unpack('<i', data[76:80])[0]

                # --- DASHBOARD RENDER ---
                # \033[H resets cursor to top
                output = f"""\033[H
============================================================
   ASSETTO CORSA TELEMETRY | Car: {car_name}
============================================================
 [ ENGINE ]
  Speed: {speed:6.1f} km/h   |   RPM:   {rpm:5.0f}
  Gear:  {get_gear_char(gear):^6}       |   Steer: {steer:5.2f}

 [ PEDALS ]
  Gas:    {'█' * int(gas * 10):<10} {gas:.2f}
  Brake:  {'█' * int(brake * 10):<10} {brake:.2f}
  Clutch: {'█' * int(clutch * 10):<10} {clutch:.2f}

 [ G-FORCE ]
  Lat: {g_lat:5.2f} G  |  Vert: {g_vert:5.2f} G  |  Long: {g_long:5.2f} G

============================================================
"""
                sys.stdout.write(output)
                sys.stdout.flush()

            # --- PACKET TYPE 2: LAP INFO (Different Size) ---
            # If we receive a packet that is NOT 328 bytes, it might be the Lap Update
            elif len(data) > 328: 
                # Attempt to parse Lap Packet (Structure varies, but usually contains Lap Time)
                # We mainly want to catch the "Spot" event which sends the completed lap
                pass 
            
            # Note: Live "Current Lap Time" is often NOT sent in the UDP stream 
            # to save bandwidth. It is calculated client-side or found in Shared Memory.
            # The UDP stream focuses on Physics.

    except KeyboardInterrupt:
        print("\nDisconnecting...")
        sock.sendto(struct.pack('<iii', 1, 1, 3), (AC_IP, AC_PORT))
    finally:
        sock.close()

if __name__ == "__main__":
    start_telemetry()