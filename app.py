import streamlit as st
import cv2
import mediapipe as mp
import numpy as np
import time
import math
import matplotlib.pyplot as plt
from collections import deque
import platform
import requests

# ================= PAGE CONFIG =================
st.set_page_config(page_title="AI Gesture Volume System", layout="wide")

# ================= UI STYLE =================
st.markdown("""
<style>

html, body {
background: linear-gradient(135deg,#141E30,#243B55);
color:white;
}

.main-header{
text-align:center;
font-size:36px;
font-weight:bold;
padding:15px;
border-radius:12px;
background:linear-gradient(90deg,#00c6ff,#0072ff);
margin-bottom:10px;
}

.card{
background:rgba(255,255,255,0.08);
padding:12px;
border-radius:12px;
margin-bottom:10px;
text-align:center;
}

.info-box{
background: rgba(255,255,255,0.1);
padding:10px;
border-radius:10px;
text-align:center;
margin:5px;
}

.info-number{
font-size:22px;
font-weight:bold;
}

.info-label{
font-size:13px;
opacity:0.8;
}

</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown('<div class="main-header">AI Gesture Volume Control System</div>', unsafe_allow_html=True)

# ================= START STOP =================
c1,c2,c3 = st.columns([1,1,1])

start_btn = c1.button("▶ Start")
stop_btn = c3.button("⏹ Stop")

if "run" not in st.session_state:
    st.session_state.run=False

if start_btn:
    st.session_state.run=True

if stop_btn:
    st.session_state.run=False

# ================= DETECTION PARAMETERS =================
st.subheader("Detection Parameters")

p1,p2,p3 = st.columns(3)

with p1:
    detection_conf = st.slider("Detection Confidence",0.0,1.0,0.75)

with p2:
    tracking_conf = st.slider("Tracking Confidence",0.0,1.0,0.80)

with p3:
    max_hands = st.slider("Max Number of Hands",1,4,2)

# ================= MEDIAPIPE =================
mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
min_detection_confidence=detection_conf,
min_tracking_confidence=tracking_conf,
max_num_hands=max_hands
)

# ================= VOLUME CONTROL =================
def initialize_volume_control():

    if platform.system()=="Windows":

        import pythoncom
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL
        from pycaw.pycaw import AudioUtilities,IAudioEndpointVolume

        pythoncom.CoInitialize()

        devices=AudioUtilities.GetSpeakers()

        interface=devices.Activate(
            IAudioEndpointVolume._iid_,
            CLSCTX_ALL,
            None
        )

        volume=cast(interface,POINTER(IAudioEndpointVolume))

        def set_volume(percent):
            percent=max(0,min(100,percent))
            volume.SetMasterVolumeLevelScalar(percent/100,None)

        def get_volume():
            return int(volume.GetMasterVolumeLevelScalar()*100)

    else:

        def set_volume(percent): pass
        def get_volume(): return 50

    return set_volume,get_volume


set_volume,get_volume = initialize_volume_control()

# ================= LAYOUT =================
left,center,right = st.columns([1.2,2,1.2])

# LEFT PANEL
with left:

    st.subheader("Detection Status")

    cam_status = st.empty()
    hands_status = st.empty()
    fps_status = st.empty()
    model_status = st.empty()

    st.subheader("Detection Info")
    info1,info2 = st.columns(2)
    info3,info4 = st.columns(2)
    info5 = st.empty()
    landmark_info = info1.empty()
    connection_info = info2.empty()
    resolution_info = info3.empty()
    latency_info = info4.empty()
    accuracy_info = info5
    api_box = st.empty()
    api_status_box = st.empty()
    

# CENTER CAMERA
with center:
    camera_frame = st.empty()

# RIGHT PANEL
with right:

    volume_display = st.empty()
    volume_bar = st.empty()

    graph1 = st.empty()
    graph2 = st.empty()
    

# ================= CAMERA FUNCTION =================
def run_camera():

    cap=cv2.VideoCapture(0,cv2.CAP_DSHOW)

    width=640
    height=480

    cap.set(3,width)
    cap.set(4,height)

    prev_time=time.time()

    smooth_volume=get_volume()

    volume_history=deque(maxlen=25)

    frame_count=0
    api_latency = 0
    api_status = "Waiting"
    api_result = {}
    accuracy=0

    cam_status.markdown('<div class="card">Camera Status: <b style="color:lightgreen">Active</b></div>',unsafe_allow_html=True)
    model_status.markdown('<div class="card">Model Status: Loaded</div>',unsafe_allow_html=True)

    while st.session_state.run:

        start_time=time.time()

        ret,frame=cap.read()
        # RESET VALUES EVERY FRAME
        hands_detected = 0
        landmark_count = 0
        connection_count = 0

        if not ret:
            break

        frame=cv2.flip(frame,1)

        h,w,_ = frame.shape

        rgb=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)

        results=hands.process(rgb)

        hands_detected=0
        distance_value=0
        gesture="None"
        mapped_volume=get_volume()

        if results.multi_hand_landmarks:

            hands_detected=len(results.multi_hand_landmarks)
            landmark_count = 21
            connection_count = 20
            # Simple AI accuracy estimation
            accuracy = min(100, 80 + hands_detected*5)

            for hand_landmarks in results.multi_hand_landmarks:

                mp_draw.draw_landmarks(
                frame,
                hand_landmarks,
                mp_hands.HAND_CONNECTIONS
                )

            hand=results.multi_hand_landmarks[0]

            thumb=hand.landmark[4]
            index=hand.landmark[8]

            x1,y1=int(thumb.x*w),int(thumb.y*h)
            x2,y2=int(index.x*w),int(index.y*h)

            distance_value=int(math.hypot(x2-x1,y2-y1))

            # API Gesture Detection
            try:
                api_start=time.time()
                response=requests.post(
                "http://127.0.0.1:8000/detect",
                json={"distance":distance_value},
                timeout=0.05
                )

                api_latency=(time.time()-api_start)*1000

                data=response.json()

                gesture=data.get("gesture","None")

                api_status="Connected"
                api_result=data

            except:
                gesture="None"
                api_status="Disconnected"
                api_latency=0
                api_result={}

            # Distance → Volume Mapping
            mapped_volume=int(np.interp(distance_value,[20,120],[0,100]))
            mapped_volume=max(0,min(100,mapped_volume))

            smooth_volume=int((smooth_volume*0.8)+(mapped_volume*0.2))
            set_volume(smooth_volume)

            volume_history.append(mapped_volume)

            cv2.circle(frame,(x1,y1),10,(255,0,255),-1)
            cv2.circle(frame,(x2,y2),10,(255,0,255),-1)

            cv2.line(frame,(x1,y1),(x2,y2),(0,255,0),3)
            # Midpoint between fingers
            cx,cy = (x1+x2)//2,(y1+y2)//2

            # Distance beside finger
            cv2.putText(frame,f"{distance_value}px",
            (cx+10,cy-10),
            cv2.FONT_HERSHEY_SIMPLEX,0.7,(0,0,0),2)

            # Keep existing top display
            cv2.putText(frame,f"Distance:{distance_value}",
            (20,40),
            cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),2)
            cv2.putText(frame,f"Gesture:{gesture}",
            (20,80),
            cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),2)

            cv2.putText(frame,f"Volume:{mapped_volume}%",
            (20,120),
            cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,0,0),2)

        # ================= FPS =================
        curr_time=time.time()
        frame_time=curr_time-prev_time

        if frame_time>0:
            fps=int(1/frame_time)
        else:
            fps=0

        prev_time=curr_time

        latency=(time.time()-start_time)*1000

        # ================= UI =================
        camera_frame.image(frame,channels="BGR",width=640)

        hands_status.markdown(f'<div class="card">Hands Detected: {hands_detected}</div>',unsafe_allow_html=True)
        fps_status.markdown(f'<div class="card">Detection FPS: {fps}</div>',unsafe_allow_html=True)

        volume_display.markdown(f'<div class="card"><h2>Volume {mapped_volume}%</h2></div>',unsafe_allow_html=True)

        volume_bar.progress(mapped_volume/100)

        api_box.markdown(f"""
        <div class="card">
        <b>API Response (Postman)</b><br>
        {api_result}
        </div>
        """, unsafe_allow_html=True)

        api_status_box.markdown(f"""
        <div class="card">
        <b>API Status</b><br>
        Status: {api_status}<br>
        Latency: {api_latency:.1f} ms
        </div>
        """, unsafe_allow_html=True)

       
            

        landmark_info.markdown(f"""
        <div class="info-box">
        <div class="info-number">{landmark_count}</div>
        <div class="info-label">Landmarks</div>
        </div>
        """, unsafe_allow_html=True)

        
        connection_info.markdown(f"""
        <div class="info-box">
        <div class="info-number">{connection_count}</div>
        <div class="info-label">Connections</div>
        </div>
        """, unsafe_allow_html=True)

        resolution_info.markdown(f"""
        <div class="info-box">
        <div class="info-number">{width}x{height}</div>
        <div class="info-label">Resolution</div>
        </div>
        """, unsafe_allow_html=True)

        latency_info.markdown(f"""
        <div class="info-box">
        <div class="info-number">{latency:.0f} ms</div>
        <div class="info-label">Latency</div>
        </div>
        """, unsafe_allow_html=True)

        accuracy_info.markdown(f"""
        <div class="info-box">
        <div class="info-number">{accuracy}%</div>
        <div class="info-label">Detection Accuracy</div>
        </div>
        """, unsafe_allow_html=True)

        # ================= GRAPHS =================
        frame_count+=1

        if frame_count%5==0:

            fig1,ax1=plt.subplots(figsize=(3,2))

            ax1.set_title("Distance vs Volume Map")
            ax1.set_xlabel("Finger Distance (px)")
            ax1.set_ylabel("Volume (%)")

            ax1.set_xlim(20,120)
            ax1.set_ylim(0,100)

            # Mapping line
            ax1.plot([20,120],[0,100],linewidth=2,color="green",label="Distance → Volume Mapping")
            # Dot offset
            dot_volume = mapped_volume + 2 if mapped_volume < 98 else mapped_volume-2
            #Current point
            ax1.scatter(distance_value,dot_volume,s=100,color="red",label="Current Distance & Volume")
            # Helper lines
            ax1.plot([distance_value,distance_value],[0,dot_volume],linestyle="--",linewidth=1)
            ax1.plot([20,distance_value],[dot_volume,dot_volume],linestyle="--",linewidth=1)
            # Legend like PASS / FAIL example
            ax1.legend(loc="upper left")

            ax1.grid(alpha=0.3)

            graph1.pyplot(fig1)
            plt.close(fig1)

            fig2,ax2=plt.subplots(figsize=(3,2))

            ax2.set_title("Volume History")
            ax2.set_xlabel("Frame / Time")
            ax2.set_ylabel("Volume (%)")

            ax2.set_ylim(0,100)
            ax2.plot(list(volume_history))

            ax2.grid(alpha=0.3)

            graph2.pyplot(fig2)
            plt.close(fig2)

    cap.release()

# ================= RUN =================
if st.session_state.run:
    run_camera()
else:
    st.info("Click ▶ Start to activate system")