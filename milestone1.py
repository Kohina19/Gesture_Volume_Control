import streamlit as st
import cv2
import mediapipe as mp
import time

st.set_page_config(page_title="Hand Detection Interface", layout="wide")

# -------------------- CSS Styling --------------------
st.markdown("""
<style>

/* Top Header */
.top-bar {
    background-color: #f1f3f6;
    padding: 12px 20px;
    border-radius: 8px;
}

/* Small Blue Buttons */
div.stButton > button {
    background-color: #1f77ff;
    color: white;
    border-radius: 6px;
    height: 35px;
    font-size: 14px;
    font-weight: 500;
}

/* Right Panel */
.side-panel {
    background-color: #f8f9fb;
    padding: 15px;
    border-radius: 10px;
}

/* Small Info Text */
.small-text {
    font-size: 14px;
    margin-bottom: 6px;
}

/* Metric Cards */
.metric-card {
    background-color: #ffffff;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    font-weight: 600;
    border: 1px solid #e0e0e0;
}

</style>
""", unsafe_allow_html=True)

# -------------------- Header --------------------
header_left, header_right = st.columns([6, 2])

with header_left:
    st.markdown('<div class="top-bar"><b>Hand Detection Interface</b></div>', unsafe_allow_html=True)

with header_right:
    c1, c2, c3 = st.columns(3)
    with c1:
        start_cam = st.button("Start Camera")
    with c2:
        stop_cam = st.button("Stop Camera")
    with c3:
        capture = st.button("Capture")

# -------------------- Layout --------------------
left_col, right_col = st.columns([4, 1.2])

# -------------------- Right Panel --------------------
with right_col:
    st.markdown('<div class="side-panel">', unsafe_allow_html=True)

    st.markdown("### Detection Status")
    cam_status = st.empty()
    hand_status = st.empty()
    fps_status = st.empty()
    model_status = st.empty()

    st.markdown("---")

    st.markdown("### Detection Parameters")
    detection_conf = st.slider("Detection Confidence", 0.0, 1.0, 0.75)
    tracking_conf = st.slider("Tracking Confidence", 0.0, 1.0, 0.80)
    max_hands = st.slider("Max Number of Hands", 1, 4, 2)

    st.markdown("---")

    st.markdown("### Detection Info")

    m1, m2 = st.columns(2)
    m3, m4 = st.columns(2)

    metric1 = m1.empty()
    metric2 = m2.empty()
    metric3 = m3.empty()
    metric4 = m4.empty()

    st.markdown('</div>', unsafe_allow_html=True)

# -------------------- MediaPipe Setup --------------------
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    min_detection_confidence=detection_conf,
    min_tracking_confidence=tracking_conf,
    max_num_hands=max_hands
)

# -------------------- Session State --------------------
if "run_camera" not in st.session_state:
    st.session_state.run_camera = False

if start_cam:
    st.session_state.run_camera = True

if stop_cam:
    st.session_state.run_camera = False

frame_placeholder = left_col.empty()

# -------------------- Camera Section --------------------

if st.session_state.run_camera:

    cap = cv2.VideoCapture(0)
    prev_time = time.time()

    while st.session_state.run_camera:
        success, frame = cap.read()
        if not success:
            st.error("Failed to access camera")
            break

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        hand_count = 0
        landmark_count = 0
        connection_count = 15

        if results.multi_hand_landmarks:
            hand_count = len(results.multi_hand_landmarks)

            for hand_landmarks in results.multi_hand_landmarks:
                landmark_count = len(hand_landmarks.landmark)

                mp_draw.draw_landmarks(
                    frame,
                    hand_landmarks,
                    mp_hands.HAND_CONNECTIONS
                )

        # FPS calculation
        curr_time = time.time()
        fps = int(1 / (curr_time - prev_time))
        prev_time = curr_time

        # ---------------- Status ----------------
        cam_status.markdown(
            '<div class="small-text">Camera Status: <b style="color:green;">Active</b></div>',
            unsafe_allow_html=True
        )

        hand_status.markdown(
            f'<div class="small-text">Hands Detected: {hand_count}</div>',
            unsafe_allow_html=True
        )

        fps_status.markdown(
            f'<div class="small-text">Detection FPS: {fps}</div>',
            unsafe_allow_html=True
        )

        model_status.markdown(
            '<div class="small-text">Model Status: Loaded</div>',
            unsafe_allow_html=True
        )

        # ---------------- Detection Info Cards ----------------
        metric1.markdown(
            f'<div class="metric-card">{landmark_count} <br>Landmarks</div>',
            unsafe_allow_html=True
        )

        metric2.markdown(
            f'<div class="metric-card">{connection_count} <br>Connections</div>',
            unsafe_allow_html=True
        )

        metric3.markdown(
            f'<div class="metric-card">640x480 <br>Resolution</div>',
            unsafe_allow_html=True
        )

        metric4.markdown(
            f'<div class="metric-card">~30ms <br>Latency</div>',
            unsafe_allow_html=True
        )

        frame_placeholder.image(frame, channels="BGR", use_container_width=True)

        # ---------------- Capture Logic ----------------
        if capture:
            cv2.imwrite("captured_frame.png", frame)
            st.toast("📸 Frame Captured Successfully!")

        time.sleep(0.03)

    cap.release()

else:
    cam_status.markdown(
        '<div class="small-text">Camera Status: <b style="color:red;">Inactive</b></div>',
        unsafe_allow_html=True
    )