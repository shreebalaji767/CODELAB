import os
import subprocess
import tempfile
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MAX_CODE_SIZE = 50_000
MAX_INPUT_SIZE = 20_000
TIMEOUT_SECONDS = 5
MAX_OUTPUT_SIZE = 50_000


def limit_output(text):
    if text is None:
        return ""

    if len(text) > MAX_OUTPUT_SIZE:
        return text[:MAX_OUTPUT_SIZE] + "\n\n[Output truncated]"

    return text


def run_process(command, stdin_text=""):
    try:
        result = subprocess.run(
            command,
            input=stdin_text,
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            cwd="/tmp"
        )

        stdout = limit_output(result.stdout)
        stderr = limit_output(result.stderr)

        if result.returncode != 0:
            if stderr:
                return stdout, stderr, result.returncode

            return stdout, f"Process exited with code {result.returncode}", result.returncode

        return stdout, stderr, 0

    except subprocess.TimeoutExpired as e:
        stdout = e.stdout or ""
        stderr = e.stderr or ""

        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")

        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")

        return (
            limit_output(stdout),
            limit_output(stderr) + "\n\nExecution timed out.",
            -1
        )

    except Exception as e:
        return "", str(e), -1


def validate_code(code):
    if not isinstance(code, str):
        return False, "Invalid code."

    if len(code.encode("utf-8")) > MAX_CODE_SIZE:
        return False, "Code is too large. Maximum size is 50 KB."

    return True, ""


def validate_input(stdin_text):
    if not isinstance(stdin_text, str):
        return False, "Invalid input."

    if len(stdin_text.encode("utf-8")) > MAX_INPUT_SIZE:
        return False, "Input is too large. Maximum size is 20 KB."

    return True, ""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    })


@app.route("/api/run", methods=["POST"])
def run_code():
    try:
        data = request.get_json(silent=True) or {}

        language = str(data.get("language", "")).lower().strip()
        code = data.get("code", "")
        stdin_text = data.get("stdin", "")

        valid, error = validate_code(code)
        if not valid:
            return jsonify({
                "success": False,
                "error": error
            }), 400

        valid, error = validate_input(stdin_text)
        if not valid:
            return jsonify({
                "success": False,
                "error": error
            }), 400

        if language == "python":
            return run_python(code, stdin_text)

        if language in ("javascript", "js"):
            return run_javascript(code, stdin_text)

        if language == "sql":
            return run_sql(code)

        if language == "c":
            return run_c(code, stdin_text)

        return jsonify({
            "success": False,
            "error": f"Unsupported language: {language}"
        }), 400

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def run_python(code, stdin_text):
    stdout, stderr, returncode = run_process(
        [
            "python3",
            "-I",
            "-S",
            "-c",
            code
        ],
        stdin_text
    )

    return jsonify({
        "success": returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": returncode
    })


def run_javascript(code, stdin_text):
    stdout, stderr, returncode = run_process(
        [
            "node",
            "--use-strict",
            "-e",
            code
        ],
        stdin_text
    )

    return jsonify({
        "success": returncode == 0,
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": returncode
    })


def run_sql(code):
    with tempfile.TemporaryDirectory() as temp_dir:
        database = os.path.join(temp_dir, "database.db")

        stdout, stderr, returncode = run_process(
            [
                "sqlite3",
                "-header",
                "-column",
                database,
                code
            ],
            ""
        )

        return jsonify({
            "success": returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": returncode
        })


def run_c(code, stdin_text):
    with tempfile.TemporaryDirectory() as temp_dir:
        source_file = os.path.join(temp_dir, "main.c")
        executable = os.path.join(temp_dir, "main")

        with open(source_file, "w", encoding="utf-8") as f:
            f.write(code)

        compile_result = subprocess.run(
            [
                "gcc",
                "-std=c17",
                "-O0",
                "-Wall",
                "-Wextra",
                source_file,
                "-o",
                executable
            ],
            text=True,
            capture_output=True,
            timeout=TIMEOUT_SECONDS
        )

        compile_stdout = limit_output(compile_result.stdout)
        compile_stderr = limit_output(compile_result.stderr)

        if compile_result.returncode != 0:
            return jsonify({
                "success": False,
                "stdout": compile_stdout,
                "stderr": compile_stderr,
                "exit_code": compile_result.returncode
            })

        stdout, stderr, returncode = run_process(
            [executable],
            stdin_text
        )

        return jsonify({
            "success": returncode == 0,
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": returncode
        })


@app.route("/api/check")
def check_runtimes():
    runtimes = {}

    commands = {
        "python": ["python3", "--version"],
        "node": ["node", "--version"],
        "gcc": ["gcc", "--version"],
        "sqlite": ["sqlite3", "--version"]
    }

    for name, command in commands.items():
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3
            )

            output = (result.stdout or result.stderr).strip()

            if output:
                runtimes[name] = output.splitlines()[0]
            else:
                runtimes[name] = "Unavailable"

        except Exception:
            runtimes[name] = "Unavailable"

    return jsonify(runtimes)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
