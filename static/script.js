
const uploadForm = document.getElementById("uploadForm");
const videoInput = document.getElementById("videoInput");
const dropZone = document.getElementById("dropZone");
const fileInfo = document.getElementById("fileInfo");
const analyzeBtn = document.getElementById("analyzeBtn");
const message = document.getElementById("message");

const progressArea = document.getElementById("progressArea");
const progressBar = document.getElementById("progressBar");
const progressText = document.getElementById("progressText");
const progressPercent = document.getElementById("progressPercent");

const emptyState = document.getElementById("emptyState");
const results = document.getElementById("results");

const allowedExtensions = ["mp4", "avi", "mov", "mkv"];

function formatSize(bytes) {
    if (bytes < 1024 * 1024) {
        return (bytes / 1024).toFixed(1) + " KB";
    }

    return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

function showMessage(text, isError = false) {
    message.textContent = text;
    message.className = isError ? "message error" : "message";
}

function displayFile(file) {
    if (!file) {
        fileInfo.classList.add("hidden");
        return false;
    }

    const extension = file.name.split(".").pop().toLowerCase();

    if (!allowedExtensions.includes(extension)) {
        showMessage("Please choose MP4, AVI, MOV or MKV.", true);
        videoInput.value = "";
        fileInfo.classList.add("hidden");
        return false;
    }

    fileInfo.textContent = `${file.name} · ${formatSize(file.size)}`;
    fileInfo.classList.remove("hidden");
    showMessage("Video selected. Click Process Video to continue.");

    return true;
}

videoInput.addEventListener("change", () => {
    displayFile(videoInput.files[0]);
});

["dragenter", "dragover"].forEach(eventName => {
    dropZone.addEventListener(eventName, event => {
        event.preventDefault();
        dropZone.classList.add("dragging");
    });
});

["dragleave", "drop"].forEach(eventName => {
    dropZone.addEventListener(eventName, event => {
        event.preventDefault();
        dropZone.classList.remove("dragging");
    });
});

dropZone.addEventListener("drop", event => {
    const file = event.dataTransfer.files[0];

    if (!file) return;

    const transfer = new DataTransfer();
    transfer.items.add(file);
    videoInput.files = transfer.files;

    displayFile(file);
});

function showResults(data) {
    emptyState.classList.add("hidden");
    results.classList.remove("hidden");

    document.getElementById("resultStatus").textContent = data.status;
    document.getElementById("resultFilename").textContent =
        "File: " + data.filename;

    document.getElementById("duration").textContent =
        data.duration + " sec";

    document.getElementById("fps").textContent =
        data.fps + " FPS";

    document.getElementById("frameCount").textContent =
        data.frame_count.toLocaleString();

    document.getElementById("resolution").textContent =
        `${data.width} × ${data.height}`;

    document.getElementById("sampledFrames").textContent =
        data.sampled_frames.toLocaleString();

    document.getElementById("resultNote").textContent = data.note;
}

uploadForm.addEventListener("submit", async event => {
    event.preventDefault();

    const file = videoInput.files[0];

    if (!displayFile(file)) return;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Processing...";
    progressArea.classList.remove("hidden");
    progressBar.style.width = "25%";
    progressText.textContent = "Uploading video...";
    progressPercent.textContent = "In progress";
    showMessage("Please wait while OpenCV processes your video.");

    const formData = new FormData();
    formData.append("video", file);

    try {
        progressBar.style.width = "55%";
        progressText.textContent = "Reading video frames...";

        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || "Video processing failed.");
        }

        progressBar.style.width = "100%";
        progressText.textContent = "Processing completed";
        progressPercent.textContent = "100%";

        showResults(data);
        showMessage(
            "Video processing successful. Actual AI fall detection is not connected."
        );
    } catch (error) {
        progressBar.style.width = "0%";
        progressText.textContent = "Processing failed";
        progressPercent.textContent = "";
        showMessage(error.message, true);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = 'Process Video <span>→</span>';
    }
});
