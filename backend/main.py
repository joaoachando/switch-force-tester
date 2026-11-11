import asyncio
import serial
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database import SessionLocal, Switch

app = FastAPI()

# Configure your serial port (adjust to your Proxmox USB passthrough device)
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

# Attempt to connect to the Arduino
try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0)
except Exception as e:
    print(f"Warning: Serial port not connected. {e}")
    ser = None

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/switches")
def read_switches(db: Session = Depends(get_db)):
    return db.query(Switch).all()


@app.websocket("/ws/tester")
async def websocket_tester(websocket: WebSocket):
    await websocket.accept()

    if ser is None or not ser.is_open:
        await websocket.send_json({"type": "status", "message": "ARDUINO_MISSING"})
    else:
        await websocket.send_json({"type": "status", "message": "READY"})

    async def serial_reader():
        try:
            while True:
                if ser and ser.in_waiting > 0:
                    try:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                    except OSError:
                        await websocket.send_json({"type": "status", "message": "USB_DISCONNECTED"})
                        break

                    if not line: continue

                    if line.startswith("<STATUS:"):
                        await websocket.send_json({"type": "status", "message": line.strip("<>").split(":")[1]})

                    elif line.startswith("<DEBUG:"):
                        # E.g., <DEBUG:SWITCH:OPEN (RELEASED)>
                        parts = line.strip("<>").split(":")
                        await websocket.send_json({"type": "debug", "sensor": parts[1], "value": parts[2]})

                    elif line.startswith("DATA:"):
                        parts = line.split(":")
                        if len(parts) == 4:
                            try:
                                await websocket.send_json({
                                    "type": "data", "direction": parts[1],
                                    "travel_mm": float(parts[2]), "force_g": float(parts[3])
                                })
                            except ValueError:
                                pass
                await asyncio.sleep(0.005)
        except Exception as e:
            print(f"Serial reader closed: {e}")

    reader_task = asyncio.create_task(serial_reader())

    try:
        while True:
            data = await websocket.receive_json()
            if ser and ser.is_open:
                cmd = data.get("command")
                val = data.get("value", "")

                # Route commands to Arduino
                if cmd == "start":
                    ser.write(b"s\n")
                elif cmd == "abort":
                    ser.write(b"x\n")
                elif cmd == "tare":
                    ser.write(b"t\n")
                elif cmd == "check_switch":
                    ser.write(b"c\n")
                elif cmd == "check_weight":
                    ser.write(b"w\n")
                elif cmd == "read_raw":
                    ser.write(b"r\n")
                elif cmd == "stream_raw":
                    ser.write(b"R\n")
                elif cmd == "jog":
                    ser.write(f"j{val}\n".encode())
                elif cmd == "set_speed":
                    ser.write(f"v{val}\n".encode())
                elif cmd == "set_accel":
                    ser.write(f"a{val}\n".encode())
            else:
                await websocket.send_json({"type": "status", "message": "ARDUINO_MISSING"})
    finally:
        reader_task.cancel()
        if ser and ser.is_open: ser.write(b"x\n")

app.mount("/static", StaticFiles(directory="static"), name="static")

# This tells FastAPI to serve your index.html when you visit the root domain
@app.get("/")
def read_root():
    return FileResponse("static/index.html")
