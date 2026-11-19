import socket
import asyncio
import json
import threading
import http.server
import socketserver
import os
import websockets
import keyboard

# 1. Jalankan Server Web Lokal (http://localhost:8000) agar izin mikrofon tersimpan permanen
def start_http_server():
    os.chdir(r"C:\aerofly_atc")
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("127.0.0.1", 8000), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

# 2. Menangkap Sinyal UDP dari Aerofly FS 4
UDP_IP = "0.0.0.0"
UDP_PORT = 49002

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

print("=== JEMBATAN AEROFLY FS 4 + LOCAL SERVER AKTIF ===")
print("-> Buka di browser: http://localhost:8000/Aerofly_Global_ATC.html")
print("-> Tekan [RIGHT CTRL] kapan saja di dalam game untuk bicara dengan ATC!")

connected_clients = set()

async def register(websocket):
    connected_clients.add(websocket)
    print("Radar HTML terhubung!")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)

async def broadcast_telemetry():
    last_ptt_state = False
    last_center_state = False

    while True:
        try:
            ptt_pressed = keyboard.is_pressed('right ctrl')
            if ptt_pressed and not last_ptt_state:
                for ws in list(connected_clients):
                    await ws.send(json.dumps({"action": "toggle_ptt"}))
            last_ptt_state = ptt_pressed

            center_pressed = keyboard.is_pressed('f9')
            if center_pressed and not last_center_state:
                for ws in list(connected_clients):
                    await ws.send(json.dumps({"action": "center_map"}))
            last_center_state = center_pressed
        except Exception:
            pass

        try:
            data, _ = sock.recvfrom(4096)
            text = data.decode('utf-8', errors='ignore').strip()
            if text.startswith("XGPS"):
                parts = text.split(",")
                if len(parts) >= 6:
                    payload = {
                        "lat": float(parts[2]),
                        "lon": float(parts[1]),
                        "altitude": round(float(parts[3]) * 3.28084),
                        "heading": float(parts[4]),
                        "speed": round(float(parts[5]) * 1.94384)
                    }
                    for ws in list(connected_clients):
                        await ws.send(json.dumps(payload))
        except BlockingIOError:
            pass
        except Exception:
            pass

        await asyncio.sleep(0.04)

async def main():
    async with websockets.serve(register, "localhost", 8765):
        await broadcast_telemetry()

if __name__ == "__main__":
    asyncio.run(main())