import os
import time
import threading
from datetime import datetime

import cv2
import mediapipe as mp
import numpy as np
from flask import Flask, render_template, request, jsonify, Response
from werkzeug.utils import secure_filename

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads_videos")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv", "webm"}

mp_pose = mp.solutions.pose
mp_draw = mp.solutions.drawing_utils
lock = threading.Lock()

state = {
    "video_path": None,
    "filename": "",
    "status": "Ready",
    "frames_total": 0,
    "frames_processed": 0,
    "fps": 0,
    "resolution": "—",
    "duration": 0,
    "fall_detected": False,
    "events": [],
    "stream_token": 0,
}


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def torso_angle(landmarks):
    """Estimate torso tilt using shoulder and hip landmarks."""
    ids = mp_pose.PoseLandmark

    points = [
        landmarks[ids.LEFT_SHOULDER.value],
        landmarks[ids.RIGHT_SHOULDER.value],
        landmarks[ids.LEFT_HIP.value],
        landmarks[ids.RIGHT_HIP.value],
    ]

    if min(point.visibility for point in points) < 0.45:
        return None

    sx = (points[0].x + points[1].x) / 2
    sy = (points[0].y + points[1].y) / 2
    hx = (points[2].x + points[3].x) / 2
    hy = (points[2].y + points[3].y) / 2

    dx = sx - hx
    dy = sy - hy

    angle = abs(np.degrees(np.arctan2(dx, -dy)))
    return float(min(angle, 180 - angle))


def add_event(message):
    event = {
        "time": datetime.now().strftime("%H:%M:%S"),
        "message": message,
    }

    with lock:
        state["events"].insert(0, event)
        state["events"] = state["events"][:30]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload():
    if "video" not in request.files:
        return jsonify({"error": "Video file missing."}), 400

    file = request.files["video"]

    if not file.filename:
        return jsonify({"error": "Please choose a video first."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": "Use MP4, AVI, MOV, MKV or WEBM format."
        }), 400

    filename = secure_filename(file.filename)
    unique_name = f"{int(time.time())}_{filename}"
    path = os.path.join(UPLOAD_DIR, unique_name)

    file.save(path)

    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        cap.release()
        os.remove(path)
        return jsonify({
            "error": "OpenCV could not read this video."
        }), 400

    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()

    with lock:
        state.update({
            "video_path": path,
            "filename": filename,
            "status": "Ready to analyse",
            "frames_total": frames,
            "frames_processed": 0,
            "fps": round(fps, 2),
            "resolution": f"{width} × {height}",
            "duration": round(frames / fps, 2) if fps > 0 else 0,
            "fall_detected": False,
            "events": [],
            "stream_token": state["stream_token"] + 1,
        })

    add_event(f"Video uploaded: {filename}")

    return jsonify({
        "message": "Video uploaded successfully.",
        "filename": filename,
        "metadata": {
            "frames": frames,
            "fps": round(fps, 2),
            "resolution": f"{width} × {height}",
            "duration": round(frames / fps, 2) if fps > 0 else 0,
        },
    })


def frame_stream(path, token):
    cap = cv2.VideoCapture(path)

    if not cap.isOpened():
        with lock:
            state["status"] = "Could not open video"
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if not fps or fps < 1:
        fps = 25

    fall_frames = 0
    threshold_frames = max(1, int(fps * 1.0))
    processed = 0

    with lock:
        state["status"] = "Analysing"
        state["fall_detected"] = False

    add_event("Analysis started")

    try:
        with mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as pose:

            while True:
                with lock:
                    if token != state["stream_token"]:
                        break

                ok, frame = cap.read()
                if not ok:
                    break

                processed += 1
                h, w = frame.shape[:2]

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = pose.process(rgb)
                angle = None

                if result.pose_landmarks:
                    mp_draw.draw_landmarks(
                        frame,
                        result.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS,
                    )

                    angle = torso_angle(
                        result.pose_landmarks.landmark
                    )

                # Basic educational posture heuristic.
                # This is not a trained fall-classification model.
                if angle is not None and angle >= 60:
                    fall_frames += 1
                else:
                    fall_frames = max(0, fall_frames - 2)

                possible_fall = fall_frames >= threshold_frames

                with lock:
                    was_fall = state["fall_detected"]
                    state["fall_detected"] = possible_fall
                    state["frames_processed"] = processed
                    state["status"] = (
                        "Possible fall detected"
                        if possible_fall
                        else "Analysing"
                    )

                if possible_fall and not was_fall:
                    add_event(
                        f"Possible fall pattern at approx. "
                        f"{processed / fps:.1f}s"
                    )

                elif was_fall and not possible_fall:
                    add_event(
                        f"Fall warning cleared at approx. "
                        f"{processed / fps:.1f}s"
                    )

                if possible_fall:
                    color = (0, 0, 255)
                    label = "POSSIBLE FALL - CHECK PERSON"
                else:
                    color = (20, 150, 50)
                    label = "MONITORING"

                cv2.rectangle(
                    frame, (8, 8), (w - 8, 72), color, -1
                )

                cv2.putText(
                    frame,
                    label,
                    (18, 35),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.72,
                    (255, 255, 255),
                    2,
                )

                if angle is not None:
                    angle_label = f"Torso tilt: {angle:.1f} deg"
                else:
                    angle_label = "Pose: not confidently detected"

                cv2.putText(
                    frame,
                    angle_label,
                    (18, 59),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.52,
                    (255, 255, 255),
                    1,
                )

                if w > 960:
                    frame = cv2.resize(
                        frame,
                        (960, int(h * 960 / w)),
                    )

                encoded, buffer = cv2.imencode(".jpg", frame)

                if encoded:
                    yield (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n\r\n"
                        + buffer.tobytes()
                        + b"\r\n"
                    )

                time.sleep(0.001)

    except Exception as exc:
        add_event(f"Processing error: {type(exc).__name__}")

        with lock:
            state["status"] = "Processing error"

    finally:
        cap.release()

        with lock:
            if (
                token == state["stream_token"]
                and state["status"] != "Processing error"
            ):
                state["status"] = "Analysis complete"

        add_event("Video analysis finished")


@app.route("/stream")
def stream():
    with lock:
        path = state["video_path"]
        token = state["stream_token"]

    if not path or not os.path.isfile(path):
        return "Upload a video first.", 400

    return Response(
        frame_stream(path, token),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={"Cache-Control": "no-cache, no-store"},
    )


@app.route("/status")
def status():
    with lock:
        return jsonify({
            "filename": state["filename"],
            "status": state["status"],
            "frames_total": state["frames_total"],
            "frames_processed": state["frames_processed"],
            "fps": state["fps"],
            "resolution": state["resolution"],
            "duration": state["duration"],
            "fall_detected": state["fall_detected"],
            "events": list(state["events"]),
        })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True,
    )