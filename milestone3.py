import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
import time
import math
import matplotlib.pyplot as plt
from collections import deque
import platform

# ---------------- OS-Specific Volume Control ----------------
system_os = platform.system()

if system_os == "Windows":
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

    devices = AudioUtilities.GetSpeakers()
    interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    volume = cast(interface, POINTER(IAudioEndpointVolume))

    def set_volume(percent):
        level = percent / 100
        volume.SetMasterVolumeLevelScalar(level, None)

    def get_volume():
        return int(volume.GetMasterVolumeLevelScalar() * 100)

elif system_os == "Darwin":
    def set_volume(percent):
        import os
        os.system(f"osascript -e 'set volume output volume {int(percent)}'")

    def get_volume():
        import subprocess
        v = subprocess.check_output(
            ["osascript", "-e", "output volume of (get volume settings)"]
        )
        return int(v)

else:  # Linux
    def set_volume(percent):
        import os
        os.system(f"amixer sset Master {int(percent)}%")

    def get_volume():
        return 50


# ---------------- STREAMLIT PAGE CONFIG ----------------
st.set_page_config(page_title="Volume Control Interface", layout="wide")

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
.header {
    background: #e9f4ff;
    padding: 18px;
    border-radius: 10px;
    font-size: 25px;
    font-weight: 700;
}
.right-card {
    background: white;
    padding: 18px;
    border-radius: 12px;
    margin-bottom: 20px;
    border: 1px solid #e0e0e0;
}
.status-green { color: #2ecc71; font-weight: 600; }
.status-blue { color: #3498db; font-weight: 600; }
.volume-box {
    background: #e8f8f5;
    padding: 20px;
    text-align: center;
    border-radius: 12px;
    font-size: 40px;
    font-weight: 700;
}
div.stButton > button {
    background-color: #009879;
    color: white;
    border-radius: 6px;
    height: 36px;
}
</style>
""", unsafe_allow_html=True)

# ---------------- HEADER ----------------
left_h, right_h = st.columns([6, 2])

with left_h:
    st.markdown('<div class="header"> Volume Control Interface </div>', unsafe_allow_html=True)

with right_h:
    c1, c2, c3 = st.columns(3)
    start_btn = c1.button("▶ Start")
    pause_btn = c2.button("⏸ Pause")
    settings_btn = c3.button("⚙ Settings")

# ---------------- LAYOUT ----------------
left_col, right_col = st.columns([4, 1.6])

# ---------------- RIGHT COLUMN ----------------
with right_col:

    st.markdown('<div class="right-card">', unsafe_allow_html=True)
    st.markdown("### Current Volume")
    volume_display = st.empty()
    st.markdown('<p class="status-green">● Active</p>', unsafe_allow_html=True)
    st.markdown('<p class="status-blue">● Synced</p>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="right-card">', unsafe_allow_html=True)
    st.markdown("### Live Preview")
    live_preview = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="right-card">', unsafe_allow_html=True)
    st.markdown("### Volume History")
    history_plot = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)

# ---------------- LEFT COLUMN ----------------
with left_col:
    st.markdown("### 📉 Distance to Volume Mapping")
    graph_placeholder = st.empty()

# ---------------- MEDIAPIPE SETUP ----------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    min_detection_confidence=0.75,
    min_tracking_confidence=0.75,
    max_num_hands=1
)

# ---------------- SESSION STATE ----------------
if "run" not in st.session_state:
    st.session_state.run = False

if start_btn:
    st.session_state.run = True

if pause_btn:
    st.session_state.run = False

volume_history = deque(maxlen=50)
smooth_volume = 0

# ---------------- CAMERA LOOP ----------------
if st.session_state.run:

    cap = cv2.VideoCapture(0)

    while st.session_state.run:

        ret, frame = cap.read()
        if not ret:
            st.error("Camera not detected")
            break

        frame = cv2.flip(frame, 1)
        h, w, _ = frame.shape
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        distance = 0
        mapped_volume = get_volume()

        if results.multi_hand_landmarks:
            hand = results.multi_hand_landmarks[0]

            x1, y1 = int(hand.landmark[4].x * w), int(hand.landmark[4].y * h)
            x2, y2 = int(hand.landmark[8].x * w), int(hand.landmark[8].y * h)

            distance = int(math.hypot(x2 - x1, y2 - y1))
            vol = np.interp(distance, [20, 120], [0, 100])

            smooth_volume = int((smooth_volume * 0.8) + (vol * 0.2))
            set_volume(smooth_volume)
            mapped_volume = smooth_volume

            cv2.circle(frame, (x1, y1), 8, (255, 0, 255), -1)
            cv2.circle(frame, (x2, y2), 8, (255, 0, 255), -1)
            cv2.line(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)

        live_preview.image(frame, channels="BGR")

        volume_display.markdown(
            f'<div class="volume-box">{mapped_volume}%</div>',
            unsafe_allow_html=True
        )

        volume_history.append(mapped_volume)

        # Mapping Graph
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 100)
        ax.grid(True, linestyle="--", alpha=0.4)
        ax.plot([0, 100], [0, 100], label="Volume %", color="teal")
        ax.scatter(distance, mapped_volume, color="orange", s=120)
        ax.legend()
        graph_placeholder.pyplot(fig)
        plt.close(fig)

        # Volume History Graph
        fig2, ax2 = plt.subplots(figsize=(4, 2))
        ax2.plot(list(volume_history), color="purple")
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        history_plot.pyplot(fig2)
        plt.close(fig2)

        time.sleep(0.02)

    cap.release()

else:
    st.info("Click Start to activate the camera")