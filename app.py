from flask import Flask, render_template, request
import subprocess
import os
import uuid
from datetime import datetime

app = Flask(__name__)

RESULTS_DIR = "results"
os.makedirs(RESULTS_DIR, exist_ok=True)


@app.route("/", methods=["GET", "POST"])
def index():
    message = ""
    result = ""
    target = ""

    if request.method == "POST":
        target = request.form.get("target", "").strip()

        if not target:
            message = "Please enter a target URL."
            return render_template("index.html", message=message, result=result, target=target)

        if not target.startswith(("http://", "https://")):
            message = "Target must start with http:// or https://"
            return render_template("index.html", message=message, result=result, target=target)

        scan_id = str(uuid.uuid4())[:8]
        output_file = os.path.join(RESULTS_DIR, f"scan_{scan_id}.txt")

        command = [
    "nuclei",
    "-u", target,
    "-t", "/root/nuclei-templates/http/technologies/",
    "-severity", "info,low",
    "-rate-limit", "5",
    "-c", "2",
    "-timeout", "5",
    "-retries", "0",
    "-o", output_file
]

        try:
            subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=40
            )

            if os.path.exists(output_file):
                with open(output_file, "r", encoding="utf-8", errors="ignore") as file:
                    result = file.read()

            if not result.strip():
                result = "Scan finished, but no results were found."

            message = "Scan completed."

        except subprocess.TimeoutExpired:
            message = "Scan timed out. Try a smaller or authorized target."

        except Exception as e:
            message = f"Error: {str(e)}"

    return render_template("index.html", message=message, result=result, target=target)


@app.route("/history")
def history():
    files = []

    for filename in os.listdir(RESULTS_DIR):
        if filename.endswith(".txt"):
            path = os.path.join(RESULTS_DIR, filename)
            files.append({
                "name": filename,
                "time": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")
            })

    files.sort(key=lambda x: x["time"], reverse=True)

    return render_template("index.html", files=files, history=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
