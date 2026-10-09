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

    # Background task to read from Arduino and send to Browser
    async def serial_reader():
        try:
            while True:
                if ser and ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8', errors='ignore').strip()
                    if not line:
                        continue

                    # Parse Status Messages
                    if line.startswith("<STATUS:"):
                        status = line.replace("<STATUS:", "").replace(">", "")
                        await websocket.send_json({"type": "status", "message": status})

                    # Parse Data Points (e.g., DATA:d:1.250:45.30)
                    elif line.startswith("DATA:"):
                        parts = line.split(":")
                        if len(parts) == 4:
                            try:
                                await websocket.send_json({
                                    "type": "data",
                                    "direction": parts[1],  # 'd', 'u', 'P', 'R'
                                    "travel_mm": float(parts[2]),
                                    "force_g": float(parts[3])
                                })
                            except ValueError:
                                pass  # Ignore bad serial reads

                await asyncio.sleep(0.005)  # Yield to event loop
        except WebSocketDisconnect:
            pass

    # Start the reader task
    reader_task = asyncio.create_task(serial_reader())

    try:
        # Listen for commands FROM the browser
        while True:
            data = await websocket.receive_json()
            if ser:
                if data.get("command") == "start":
                    ser.write(b's')
                elif data.get("command") == "abort":
                    ser.write(b'x')

    except WebSocketDisconnect:
        print("Client disconnected")
    finally:
        reader_task.cancel()
        if ser:
            ser.write(b'x')  # Abort motor if browser closes

app.mount("/static", StaticFiles(directory="static"), name="static")

# This tells FastAPI to serve your index.html when you visit the root domain
@app.get("/")
def read_root():
    return FileResponse("static/index.html")
