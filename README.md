# SafeStep AI – Fall Detection System

## Project Overview
SafeStep AI is an AI-based fall detection project designed to analyze uploaded videos and identify potential fall events using computer vision techniques.

## Technologies Used
- Python
- Flask
- OpenCV
- MediaPipe
- HTML, CSS and JavaScript

## Features
- Video upload and analysis
- Computer vision-based human pose analysis
- Fall detection analysis results
- Analysis status and event log dashboard

## Project Structure
- `app.py` – Flask application and backend logic
- `requirements.txt` – Python dependencies
- `templates/` – HTML templates
- `static/` – CSS, JavaScript and other static assets
- `uploads/` – Uploaded videos, if used locally

## Installation and Setup

1. Install Python 3.11.
2. Clone or download this repository.
3. Open the project folder in VS Code.
4. Create and activate a virtual environment.

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv311
.\.venv311\Scripts\Activate.ps1
```

5. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

6. Run the application:

```powershell
python app.py
```

7. Open the local URL shown in the terminal, usually `http://127.0.0.1:5000`.

## Disclaimer
This project is intended for academic demonstration. Fall detection results should be verified by a human observer and must not be treated as a substitute for professional emergency monitoring.
