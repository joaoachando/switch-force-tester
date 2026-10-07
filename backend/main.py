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

    # Send a command to the Arduino to start the stepper motor
    if ser:
        ser.write(b"START\n") # Adjust this string to match your Geekboards fork

    try:
        while True:
            # Read serial data without blocking the async event loop
            if ser and ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                if line:
                    # Stream the raw data point (e.g., "1.20,45.5") to the frontend chart
                    await websocket.send_text(line)

            # Yield control back to the event loop so the server stays responsive
            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        print("Browser client disconnected")
        # Safety catch: tell the Arduino to stop if the user closes the tab
        if ser:
            ser.write(b"STOP\n")

app.mount("/static", StaticFiles(directory="static"), name="static")

# This tells FastAPI to serve your index.html when you visit the root domain
@app.get("/")
def read_root():
    return FileResponse("static/index.html")
