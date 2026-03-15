from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# ================= INPUT MODEL =================
class GestureInput(BaseModel):
    distance: int


# ================= ROOT =================
@app.get("/")
def home():
    return {"message": "Gesture API is running"}


# ================= DETECT GESTURE =================
@app.post("/detect")
def detect_gesture(data: GestureInput):

    distance = data.distance

    # Gesture Logic
    if distance < 30:
        gesture = "Closed Hand"
        volume = 10

    elif distance < 80:
        gesture = "Pinch Gesture"
        volume = 50

    else:
        gesture = "Open Hand"
        volume = 100

    return {
        "distance": distance,
        "gesture": gesture,
        "volume": volume
    }