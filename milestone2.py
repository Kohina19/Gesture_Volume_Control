import streamlit as st
import cv2
import mediapipe as mp
import time
import math

st.set_page_config(page_title="Gesture Recognition Interface", layout="wide")

# -------------------- CSS --------------------
st.markdown("""
<style>

/* Header */
.header {
    background: linear-gradient(90deg, #6a11cb, #8e44ad);
    padding: 15px;
    border-radius: 10px;
    color: white;
}

/* Buttons */
div.stButton > button {
    background-color: #6a11cb;
    color: white;
    border-radius: 6px;
    height: 35px;
    font-weight: 500;
}

/* Right Panel */
.side-panel {
    background-color: #f5f6fa;
    padding: 15px;
    border-radius: 12px;
}

/* Cards */
.card {
    background-color: white;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
    margin-bottom: 15px;
}

/* Gesture Labels */
.badge {
    padding: 6px 12px;
    border-radius: 20px;
    color: white;
    font-size: 14px;
    display: inline-block;
}

/* Gesture Colors */
.green {background-color:#2ecc71;}
.orange {background-color:#f39c12;}
.red {background-color:#e74c3c;}

/* Progress Bar */
.progress {
    height: 8px;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

# -------------------- HEADER --------------------
left_h, right_h = st.columns([6,2])

with left_h:
    st.markdown('<div class="header"><h3>Gesture Recognition Interface</h3></div>', unsafe_allow_html=True)

with right_h:
    c1, c2, c3 = st.columns(3)
    start_cam = c1.button("▶ Start")
    stop_cam = c2.button("⏸ Pause")
    capture = c3.button("⚙ Settings")

# -------------------- LAYOUT --------------------
left_col, right_col = st.columns([4,1.3])

# -------------------- RIGHT PANEL --------------------
with right_col:
    st.markdown('<div class="side-panel">', unsafe_allow_html=True)

    # Distance Card
    st.markdown("### 📏 Distance Measurement")
    dist_card = st.empty()
    progress_bar = st.progress(0)

    st.markdown("---")

    # Gesture States
    st.markdown("### ✋ Gesture States")
    gesture_state = st.empty()

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- MediaPipe --------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    min_detection_confidence=0.75,
    min_tracking_confidence=0.8,
    max_num_hands=2
)

# -------------------- Gesture Logic --------------------
def classify_gesture(distance):
    if distance < 30:
        return "Closed", "red"
    elif distance < 80:
        return "Pinch", "orange"
    else:
        return "Open Hand", "green"

# -------------------- Session --------------------
if "run_camera" not in st.session_state:
    st.session_state.run_camera = False

if start_cam:
    st.session_state.run_camera = True

if stop_cam:
    st.session_state.run_camera = False

frame_placeholder = left_col.empty()

# -------------------- CAMERA --------------------
if st.session_state.run_camera:

    cap = cv2.VideoCapture(0)
    prev_time = time.time()

    while st.session_state.run_camera:
        success, frame = cap.read()
        if not success:
            st.error("Camera error")
            break

        frame = cv2.flip(frame,1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        distance_value = 0
        gesture_name = "None"
        color_class = "green"

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:

                h,w,_ = frame.shape

                thumb = hand_landmarks.landmark[4]
                index = hand_landmarks.landmark[8]

                x1,y1 = int(thumb.x*w), int(thumb.y*h)
                x2,y2 = int(index.x*w), int(index.y*h)

                # Distance
                distance_value = int(math.hypot(x2-x1, y2-y1))

                # Gesture
                gesture_name, color_class = classify_gesture(distance_value)

                # Draw
                cv2.circle(frame,(x1,y1),8,(255,0,255),-1)
                cv2.circle(frame,(x2,y2),8,(255,0,255),-1)
                cv2.line(frame,(x1,y1),(x2,y2),(255,0,0),3)

                cx,cy = (x1+x2)//2,(y1+y2)//2

                cv2.putText(frame,f"{distance_value} mm",
                            (cx-40,cy-10),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,(0,255,255),2)

                # Gesture Tag
                cv2.rectangle(frame,(10,10),(200,60),(120,0,200),-1)
                cv2.putText(frame,f"{gesture_name} Gesture",
                            (20,45),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,(255,255,255),2)

                mp_draw.draw_landmarks(frame,hand_landmarks,mp_hands.HAND_CONNECTIONS)

        # ---------------- UI UPDATE ----------------

        # Distance card
        dist_card.markdown(f"""
        <div class="card">
            <h2>{distance_value}</h2>
            <p>millimeters</p>
        </div>
        """, unsafe_allow_html=True)

        # Progress bar (0-100)
        progress = min(distance_value/100,1.0)
        progress_bar.progress(progress)

        # Gesture states panel
        gesture_state.markdown(f"""
        <div class="card">
            <p><span class="badge green">●</span> Open Hand <br><small>Distance > 80mm</small></p>
            <p><span class="badge orange">●</span> Pinch <br><small>20mm - 80mm</small></p>
            <p><span class="badge red">●</span> Closed <br><small>< 20mm</small></p>
            <hr>
            <h4>Current: <span class="{color_class} badge">{gesture_name}</span></h4>
        </div>
        """, unsafe_allow_html=True)

        # Show frame
        frame_placeholder.image(frame, channels="BGR", use_container_width=True)

        time.sleep(0.03)

    cap.release()

else:
    st.info("Click Start to activate camera")