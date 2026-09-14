import os
import subprocess
import tempfile
from flask import Flask, jsonify, render_template, request


app = Flask(__name__)

PORT = int(os.environ.get("PORT", "10000"))

MAX_CODE_SIZE = 50000
MAX_INPUT_SIZE = 20000
MAX_OUTPUT_SIZE = 50000

RUN_TIMEOUT = 5
COMPILE_TIMEOUT = 5


def clean_output(value):
    if value is None:
        return ""

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")

    value = str(value)

    if len(value) > MAX_OUTPUT_SIZE:
        return value[:MAX_OUTPUT_SIZE] + "\n\n[Output truncated]"

    return value


def run_process(command, stdin_text="", cwd=None, timeout=RUN_TIMEOUT):
    try:
        result = subprocess.run(
            command,
            input=stdin_text,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout
        )

        return {
            "stdout": clean_output(result.stdout),
            "stderr": clean_output(result.stderr),
            "exit_code": result.returncode,
            "timeout": False
        }

    except subprocess.TimeoutExpired as error:
        stdout = clean_output(error.stdout)
        stderr = clean_output(error.stderr)

        if stderr:
            stderr += "\n\n"

        stderr += "Execution timed out."

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": -1,
            "timeout": True
        }

    except Exception as error:
        return {
            "stdout": "",
            "stderr": str(error),
            "exit_code": -1,
            "timeout": False
        }


def validate_request(code, stdin_text):
    if not isinstance(code, str):
        return False, "Invalid code."

    if len(code.encode("utf-8")) > MAX_CODE_SIZE:
        return False, "Code is too large. Maximum size is 50 KB."

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


# ============================================================
# PYTHON
# ============================================================

def run_python(code, stdin_text):
    result = run_process(
        [
            "python3",
            "-I",
            "-S",
            "-c",
            code
        ],
        stdin_text=stdin_text,
        timeout=RUN_TIMEOUT
    )

    return jsonify({
        "success": (
            result["exit_code"] == 0
            and not result["timeout"]
        ),
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "exit_code": result["exit_code"]
    })


# ============================================================
# C
# ============================================================

def run_c(code, stdin_text):
    with tempfile.TemporaryDirectory() as temp_dir:

        source_file = os.path.join(
            temp_dir,
            "main.c"
        )

        executable_file = os.path.join(
            temp_dir,
            "main"
        )

        with open(
            source_file,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(code)

        try:
            compile_result = subprocess.run(
                [
                    "gcc",
                    "-std=c17",
                    "-O0",
                    "-Wall",
                    "-Wextra",
                    source_file,
                    "-o",
                    executable_file
                ],
                text=True,
                capture_output=True,
                timeout=COMPILE_TIMEOUT
            )

        except subprocess.TimeoutExpired:
            return jsonify({
                "success": False,
                "stdout": "",
                "stderr": "Compilation timed out.",
                "exit_code": -1
            })

        except Exception as error:
            return jsonify({
                "success": False,
                "stdout": "",
                "stderr": str(error),
                "exit_code": -1
            })

        if compile_result.returncode != 0:
            return jsonify({
                "success": False,
                "stdout": clean_output(
                    compile_result.stdout
                ),
                "stderr": clean_output(
                    compile_result.stderr
                ),
                "exit_code": compile_result.returncode
            })

        result = run_process(
            [
                executable_file
            ],
            stdin_text=stdin_text,
            cwd=temp_dir,
            timeout=RUN_TIMEOUT
        )

        return jsonify({
            "success": (
                result["exit_code"] == 0
                and not result["timeout"]
            ),
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"]
        })


# ============================================================
# API
# ============================================================

@app.route("/api/run", methods=["POST"])
def api_run():

    try:
        data = request.get_json(
            silent=True
        )

        if not isinstance(data, dict):
            return jsonify({
                "success": False,
                "error": "Invalid request."
            }), 400

        language = str(
            data.get("language", "")
        ).strip().lower()

        code = data.get(
            "code",
            ""
        )

        stdin_text = data.get(
            "stdin",
            ""
        )

        if code is None:
            code = ""

        if stdin_text is None:
            stdin_text = ""

        code = str(code)
        stdin_text = str(stdin_text)

        valid, error = validate_request(
            code,
            stdin_text
        )

        if not valid:
            return jsonify({
                "success": False,
                "error": error
            }), 400

        if not code.strip():
            return jsonify({
                "success": False,
                "error": "Please enter code."
            }), 400

        if language == "python":
            return run_python(
                code,
                stdin_text
            )

        if language == "c":
            return run_c(
                code,
                stdin_text
            )

        return jsonify({
            "success": False,
            "error": "This language runs in the browser."
        }), 400

    except Exception as error:

        return jsonify({
            "success": False,
            "error": str(error)
        }), 500


# ============================================================
# RUNTIME CHECK
# ============================================================

@app.route("/api/check")
def check():

    runtimes = {}

    commands = {
        "python": ["python3", "--version"],
        "gcc": ["gcc", "--version"]
    }

    for name, command in commands.items():

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3
            )

            text = (
                result.stdout
                or result.stderr
                or ""
            ).strip()

            if text:
                runtimes[name] = text.splitlines()[0]
            else:
                runtimes[name] = "Unavailable"

        except Exception:
            runtimes[name] = "Unavailable"

    return jsonify(runtimes)


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
