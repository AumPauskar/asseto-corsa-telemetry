import socket
import struct
import time
import math

# Configuration
HOST = "127.0.0.1"
PORT = 9996

def create_physics_packet(t):
    """
    Creates a valid 328-byte Assetto Corsa UDP packet with simulated data.
    't' is time, used to generate sine waves for movement.
    """
    # Create an empty buffer of 328 bytes
    packet = bytearray(328)

    # --- SIMULATION LOGIC ---
    # Simulate a car accelerating from 0 to 200 kmh and braking
    cycle = t % 10.0 # 10 second loop
    
    if cycle < 5.0: # Accelerating
        speed = (cycle / 5.0) * 200.0
        gas = 1.0
        brake = 0.0
        rpm = 1000 + (cycle * 1200) # Fake RPM rise
    else: # Braking
        speed = 200.0 - ((cycle - 5.0) / 5.0 * 200.0)
        gas = 0.0
        brake = 0.8
        rpm = 6000 - ((cycle - 5.0) * 1000)

    # Automatic Gear Shifting simulation (0=R, 1=N, 2=1st...)
    if speed < 1: gear = 1 # Neutral
    elif speed < 60: gear = 2 # 1st
    elif speed < 120: gear = 3 # 2nd
    else: gear = 4 # 3rd

    # --- PACKING DATA (Little Endian) ---
    
    # 1. Speed (Offset 8, Float)
    struct.pack_into('<f', packet, 8, speed)

    # 2. Gas (Offset 56, Float)
    struct.pack_into('<f', packet, 56, gas)

    # 3. Brake (Offset 60, Float)
    struct.pack_into('<f', packet, 60, brake)

    # 4. RPM (Offset 68, Float)
    struct.pack_into('<f', packet, 68, rpm)

    # 5. Gear (Offset 76, Int)
    struct.pack_into('<i', packet, 76, gear)

    return packet

def run_server():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, PORT))
    print(f"Server (Fake AC) listening on {HOST}:{PORT}")
    print("Waiting for client handshake...")

    client_addr = None
    active = False
    start_time = time.time()

    try:
        while True:
            # Non-blocking receive for new commands
            sock.settimeout(0.016) # ~60Hz tick
            try:
                data, addr = sock.recvfrom(4096)
                
                # Unpack command (Handshake is 3 ints: id, ver, op)
                if len(data) == 12:
                    _, _, op_id = struct.unpack('<iii', data)
                    
                    if op_id == 0: # Handshake
                        print(f"Handshake received from {addr}")
                        # Respond with Car Name (UTF-16)
                        # We send 100 chars (200 bytes) of UTF-16 text
                        car_name = "SIMULATED_FERRARI_GT3".encode('utf-16')[2:] # [2:] removes BOM
                        padding = b'\x00' * (4096 - len(car_name)) # Fill rest of packet
                        sock.sendto(car_name + padding, addr)
                        
                    elif op_id == 1: # Subscribe
                        print(f"Client {addr} subscribed to updates.")
                        client_addr = addr
                        active = True

                    elif op_id == 3: # Dismiss
                        print(f"Client {addr} disconnected.")
                        active = False
                        client_addr = None

            except socket.timeout:
                pass # No incoming command, proceed to send data if active

            # Send Telemetry Stream if active
            if active and client_addr:
                t = time.time() - start_time
                packet = create_physics_packet(t)
                sock.sendto(packet, client_addr)
                
                # Simulate 60Hz update rate
                # (The socket timeout above handles most of the delay, 
                # but this prevents CPU spanning if no timeout occurs)
                # time.sleep(0.001) 

    except KeyboardInterrupt:
        print("\nStopping Server.")
    finally:
        sock.close()

if __name__ == "__main__":
    run_server()