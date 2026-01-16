import asyncio
import websockets
import socket
import struct
import json

# --- CONFIGURATION ---
AC_IP = "127.0.0.1"
AC_PORT = 9996
WEB_PORT = 5678 # Port for the browser to connect to

# --- AC UDP SETUP ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setblocking(False) # Important for Asyncio

def get_gear_char(raw_gear):
    if raw_gear == 0: return "R"
    elif raw_gear == 1: return "N"
    else: return str(raw_gear - 1)

async def ac_telemetry_server(websocket):
    print("Browser connected!")
    
    # Handshake with AC
    try:
        sock.sendto(struct.pack('<iii', 1, 1, 0), (AC_IP, AC_PORT)) # Handshake
        sock.sendto(struct.pack('<iii', 1, 1, 1), (AC_IP, AC_PORT)) # Subscribe Update
    except BlockingIOError:
        pass

    try:
        while True:
            try:
                # Try to read from AC UDP (Non-blocking)
                data, _ = sock.recvfrom(4096)

                if len(data) == 328:
                    # --- UNPACK DATA ---
                    speed = struct.unpack('<f', data[8:12])[0]
                    g_lat = struct.unpack('<f', data[24:28])[0]
                    g_long = struct.unpack('<f', data[32:36])[0]
                    gas = struct.unpack('<f', data[56:60])[0]
                    brake = struct.unpack('<f', data[60:64])[0]
                    clutch = 1.0 - struct.unpack('<f', data[64:68])[0]
                    rpm = struct.unpack('<f', data[68:72])[0]
                    steer = struct.unpack('<f', data[72:76])[0]
                    gear = struct.unpack('<i', data[76:80])[0]

                    # --- PREPARE JSON ---
                    telemetry_data = {
                        "speed": round(speed, 1),
                        "rpm": int(rpm),
                        "gear": get_gear_char(gear),
                        "gas": round(gas, 2),
                        "brake": round(brake, 2),
                        "clutch": round(clutch, 2),
                        "steer": round(steer, 2),
                        "g_lat": round(g_lat, 2),
                        "g_long": round(g_long, 2)
                    }

                    # Send to Browser
                    await websocket.send(json.dumps(telemetry_data))

            except BlockingIOError:
                # No data from AC yet, wait a tiny bit
                await asyncio.sleep(0.001)
            except Exception as e:
                print(f"Error: {e}")
                break
                
    except websockets.exceptions.ConnectionClosed:
        print("Browser disconnected")

async def main():
    print(f"Starting Bridge...")
    print(f"1. Open Assetto Corsa")
    print(f"2. Open 'dashboard.html' in your browser")
    async with websockets.serve(ac_telemetry_server, "localhost", WEB_PORT):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass