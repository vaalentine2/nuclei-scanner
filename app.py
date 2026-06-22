from flask import Flask, render_template, request, url_for, abort
import subprocess
import json
import os
from datetime import datetime, timezone

app = Flask(__name__)

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info", "unknown"]


def run_nuclei(target):
    """Run nuclei with JSONL output and return parsed finding objects."""
    command = [
        "nuclei",
        "-u", target,
        "-jsonl",        # machine-readable: one JSON object per finding
        "-silent",
        "-timeout", "5",
        "-retries", "1",
        "-no-color",
    ]

    completed = subprocess.run(
        command, capture_output=True, text=True, timeout=120
    )

    findings = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            findings.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return findings


def simplify(findings):
    """Keep only the fields we display/store, sorted by severity."""
    rows = []
    for f in findings:
        info = f.get("info", {}) or {}
        rows.append({
            "template_id": f.get("template-id", ""),
            "name": info.get("name", ""),
            "severity": (info.get("severity") or "unknown").lower(),
            "matched_at": f.get("matched-at") or f.get("host", ""),
            "type": f.get("type", ""),
        })
    rank = {s: i for i, s in enumerate(SEVERITY_ORDER)}
    rows.sort(key=lambda r: rank.get(r["severity"], len(SEVERITY_ORDER)))
    return rows


def summarize(rows):
    counts = {sev: 0 for sev in SEVERITY_ORDER}
    for r in rows:
        sev = r["severity"] if r["severity"] in counts else "unknown"
        counts[sev] += 1
    return counts


@app.route("/", methods=["GET", "POST"])
def index():
    report = None
    error = None

    if request.method == "POST":
        target = request.form.get("target", "").strip()
        if not target:
            error = "Please enter a target."
        else:
            try:
                rows = simplify(run_nuclei(target))
                scan_id = "scan-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                report = {
                    "scan_id": scan_id,
                    "target": target,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "total": len(rows),
                    "summary": summarize(rows),
                    "findings": rows,
                }
                with open(os.path.join(RESULTS_DIR, scan_id + ".json"), "w", encoding="utf-8") as fh:
                    json.dump(report, fh, indent=2)
            except subprocess.TimeoutExpired:
                error = "Scan timed out. Try a smaller or authorized target."
            except Exception as e:
                error = f"Error: {e}"

    return render_template("index.html", report=report, error=error, severities=SEVERITY_ORDER)


@app.route("/history")
def history():
    scans = []
    for name in os.listdir(RESULTS_DIR):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(RESULTS_DIR, name), encoding="utf-8") as fh:
                data = json.load(fh)
            scans.append({
                "scan_id": data.get("scan_id", name[:-5]),
                "target": data.get("target", ""),
                "timestamp": data.get("timestamp", ""),
                "total": data.get("total", 0),
            })
        except Exception:
            continue
    scans.sort(key=lambda s: s["timestamp"], reverse=True)
    return render_template("history.html", scans=scans)


@app.route("/report/<scan_id>")
def report(scan_id):
    # block path traversal — only allow our own scan ids
    if not scan_id.startswith("scan-") or any(c in scan_id for c in "/\\.") and ".." in scan_id:
        abort(404)
    path = os.path.join(RESULTS_DIR, scan_id + ".json")
    if not os.path.isfile(path):
        abort(404)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return render_template("index.html", report=data, error=None, severities=SEVERITY_ORDER)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
