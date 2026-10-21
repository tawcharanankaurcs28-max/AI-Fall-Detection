
from flask import Flask, render_template, request, jsonify
import cv2
import os
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"mp4", "avi", "mov", "mkv"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze_video():
    if "video" not in request.files:
        return jsonify({"error": "Please select a video."}), 400

    video = request.files["video"]

    if not video.filename:
        return jsonify({"error": "No video selected."}), 400

    if not allowed_file(video.filename):
        return jsonify({
            "error": "Upload an MP4, AVI, MOV or MKV video."
        }), 400

    filename = f"{uuid.uuid4().hex}_{os.path.basename(video.filename)}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    video.save(filepath)

    cap = cv2.VideoCapture(filepath)

    if not cap.isOpened():
        cap.release()
        os.remove(filepath)
        return jsonify({"error": "Could not read this video."}), 400

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    duration = frame_count / fps if fps and fps > 0 else 0

    # Read one frame every approximately one second.
    sample_step = max(int(fps), 1) if fps and fps > 0 else 1
    sampled_frames = 0
    frame_index = 0

    while True:
        success, frame = cap.read()

        if not success:
            break

        if frame_index % sample_step == 0:
            # Frame is read by OpenCV. Fall detection is not implemented yet.
            sampled_frames += 1

        frame_index += 1

    cap.release()
    os.remove(filepath)

    return jsonify({
        "success": True,
        "filename": os.path.basename(video.filename),
        "duration": round(duration, 2),
        "fps": round(fps, 2) if fps and fps > 0 else 0,
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "sampled_frames": sampled_frames,
        "status": "Video processed successfully",
        "note": "OpenCV video processing completed. AI fall detection is not connected yet."
    })


if __name__ == "__main__":
    app.run(debug=True)
