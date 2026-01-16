import socket
import struct
import time
import math

# Configuration
HOST = "127.0.0.1"
PORT = 9996

def get_simulated_packet(t):
    """
    Generates a 328-byte packet with data matching your client's unpacking logic.
    """
    packet = bytearray(328)
    
    # --- SIMULATION LOOP (10 Seconds) ---
    cycle = t % 10.0
    
    # 1. Input Simulation
    # 0-4s: Accelerate | 4-5s: Coast | 5-9s: Brake | 9-10s: Idle
    if cycle < 4.0:
        gas = 1.0
        brake = 0.0
        rpm = 1000 + (cycle * 1500) # Rev up to 7000
        speed = cycle * 50.0 # 0 to 200 kmh
        g_long = 0.8 # G-Force pushing back
    elif cycle < 5.0:
        gas = 0.0
        brake = 0.0
        rpm = 6000
        speed = 200.0
        g_long = 0.0
    elif cycle < 9.0:
        gas = 0.0
        brake = 0.8 # Hard braking
        rpm = 6000 - ((cycle - 5.0) * 1200)
        speed = 200.0 - ((cycle - 5.0) * 50.0)
        g_long = -1.2 # G-Force pushing forward
    else:
        gas = 0.0
        brake = 0.0
        rpm = 850
        speed = 0.0
        g_long = 0.0

    # 2. Steering & Lateral G Simulation (Sine wave)
    steer = math.sin(t) # -1.0 to 1.0
    g_lat = steer * 1.5 # 1.5 Gs in corners
    g_vert = 1.0 + (math.sin(t * 10) * 0.05) # Simulated bumps ~1G

    # 3. Gear Logic
    if speed < 1: gear = 1 # Neutral
    elif speed < 60: gear = 2 # 1st
    elif speed < 120: gear = 3 # 2nd
    else: gear = 4 # 3rd

    # 4. Clutch Logic
    # Your client does: clutch = 1.0 - raw_clutch
    # So if we want clutch NOT pressed (0.0 on screen), we send 1.0 raw.
    raw_clutch = 1.0 

    # --- PACKING DATA (Little Endian) ---
    
    # Speed (Offset 8)
    struct.pack_into('<f', packet, 8, speed)

    # G-Forces (Offsets 24, 28, 32)
    struct.pack_into('<f', packet, 24, g_lat)  # Lat
    struct.pack_into('<f', packet, 28, g_vert) # Vert
    struct.pack_into('<f', packet, 32, g_long) # Long

    # Inputs (Offsets 56, 60, 64)
    struct.pack_into('<f', packet, 56, gas)
    struct.pack_into('<f', packet, 60, brake)
    struct.pack_into('<f', packet, 64, raw_clutch)

    # RPM (Offset 68)
    struct.pack_into('<f', packet, 68, rpm)

    # Steer (Offset 72)
    struct.pack_into('<f', packet, 72, steer)

    # Gear (Offset 76)
    struct.pack_into('<i', packet, 76, gear)

    return packet

def run_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"MOCK SERVER listening on {HOST}:{PORT}")
    print("Run your client script now...")

    client_addr = None
    active = False
    start_time = time.time()

    try:
        while True:
            # Check for incoming commands (Handshake/Subscribe)
            sock.settimeout(0.01)
            try:
                data, addr = sock.recvfrom(4096)
                
                if len(data) == 12: # Standard Command Packet
                    _, _, op_id = struct.unpack('<iii', data)
                    
                    if op_id == 0: # Handshake
                        print(f"-> Handshake from {addr}")
                        # Send Car Name "TEST_CAR_GT3"
                        car_name = "TEST_CAR_GT3".encode('utf-16')[2:]
                        padding = b'\x00' * (4096 - len(car_name))
                        sock.sendto(car_name + padding, addr)
                        
                    elif op_id == 1: # Subscribe Update
                        print(f"-> Client {addr} subscribed to TELEMETRY.")
                        client_addr = addr
                        active = True
                        
                    elif op_id == 2: # Subscribe Spot (Lap)
                        print(f"-> Client {addr} subscribed to LAP INFO.")
                        
            except socket.timeout:
                pass

            # Send Physics Stream
            if active and client_addr:
                t = time.time() - start_time
                packet = get_simulated_packet(t)
                sock.sendto(packet, client_addr)
                time.sleep(0.02) # ~50Hz update rate

    except KeyboardInterrupt:
        print("\nStopping Server.")
    finally:
        sock.close()

if __name__ == "__main__":
    run_server()