from flask import Flask, render_template, request
import subprocess

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():
    result = ""

    if request.method == "POST":
        target = request.form.get("target", "").strip()

        if not target:
            result = "Please enter a target."
        else:
            try:
                command = [
                    "nuclei",
                    "-u", target,
                    "-silent",
                    "-timeout", "5",
                    "-retries", "1",
                    "-no-color"
                ]

                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                output = completed.stdout.strip()
                error = completed.stderr.strip()

                if output:
                    result = output
                elif error:
                    result = error
                else:
                    result = "Scan completed. No vulnerabilities found."

            except subprocess.TimeoutExpired:
                result = "Scan timed out after 60 seconds. Try a smaller or authorized target."
            except Exception as e:
                result = f"Error: {e}"

    return render_template("index.html", result=result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
