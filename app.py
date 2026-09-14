import os
import subprocess
import tempfile
import textwrap

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(os.environ.get("PORT", "10000"))

MAX_CODE_SIZE = 50_000
MAX_INPUT_SIZE = 20_000
MAX_OUTPUT_SIZE = 50_000

EXECUTION_TIMEOUT = 5
COMPILE_TIMEOUT = 5


# ============================================================
# BASIC HELPERS
# ============================================================

def truncate_output(value):
    if value is None:
        return ""

    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")

    value = str(value)

    if len(value) > MAX_OUTPUT_SIZE:
        return value[:MAX_OUTPUT_SIZE] + "\n\n[Output truncated]"

    return value


def validate_code(code):
    if not isinstance(code, str):
        return False, "Invalid code."

    if len(code.encode("utf-8")) > MAX_CODE_SIZE:
        return False, "Code is too large. Maximum allowed size is 50 KB."

    return True, ""


def validate_stdin(stdin):
    if stdin is None:
        stdin = ""

    if not isinstance(stdin, str):
        stdin = str(stdin)

    if len(stdin.encode("utf-8")) > MAX_INPUT_SIZE:
        return False, "Input is too large. Maximum allowed size is 20 KB."

    return True, ""


def execute_process(command, stdin_text="", cwd=None, timeout=EXECUTION_TIMEOUT):
    try:
        process = subprocess.run(
            command,
            input=stdin_text,
            text=True,
            capture_output=True,
            cwd=cwd,
            timeout=timeout
        )

        stdout = truncate_output(process.stdout)
        stderr = truncate_output(process.stderr)

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": process.returncode,
            "timed_out": False
        }

    except subprocess.TimeoutExpired as error:
        stdout = error.stdout or ""
        stderr = error.stderr or ""

        stdout = truncate_output(stdout)
        stderr = truncate_output(stderr)

        if stderr:
            stderr += "\n\n"

        stderr += "Execution timed out."

        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": -1,
            "timed_out": True
        }

    except FileNotFoundError as error:
        return {
            "stdout": "",
            "stderr": f"Runtime not found: {error}",
            "exit_code": -1,
            "timed_out": False
        }

    except Exception as error:
        return {
            "stdout": "",
            "stderr": str(error),
            "exit_code": -1,
            "timed_out": False
        }


# ============================================================
# PAGES
# ============================================================

@app.route("/")
def home():
    return render_template("index.html")


# ============================================================
# HEALTH CHECK
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    })


# ============================================================
# PYTHON
# ============================================================

def execute_python(code, stdin_text):
    result = execute_process(
        [
            "python3",
            "-I",
            "-S",
            "-c",
            code
        ],
        stdin_text=stdin_text,
        timeout=EXECUTION_TIMEOUT
    )

    return jsonify({
        "success": (
            result["exit_code"] == 0
            and not result["timed_out"]
        ),
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "exit_code": result["exit_code"]
    })


# ============================================================
# JAVASCRIPT
# ============================================================

def execute_javascript(code, stdin_text):
    result = execute_process(
        [
            "node",
            "--use-strict",
            "-e",
            code
        ],
        stdin_text=stdin_text,
        timeout=EXECUTION_TIMEOUT
    )

    return jsonify({
        "success": (
            result["exit_code"] == 0
            and not result["timed_out"]
        ),
        "stdout": result["stdout"],
        "stderr": result["stderr"],
        "exit_code": result["exit_code"]
    })


# ============================================================
# SQL
# ============================================================

def execute_sql(code):
    with tempfile.TemporaryDirectory() as temp_dir:

        database_file = os.path.join(
            temp_dir,
            "codelab.db"
        )

        result = execute_process(
            [
                "sqlite3",
                "-header",
                "-column",
                database_file,
                code
            ],
            stdin_text="",
            cwd=temp_dir,
            timeout=EXECUTION_TIMEOUT
        )

        return jsonify({
            "success": (
                result["exit_code"] == 0
                and not result["timed_out"]
            ),
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"]
        })


# ============================================================
# C
# ============================================================

def execute_c(code, stdin_text):

    with tempfile.TemporaryDirectory() as temp_dir:

        source_file = os.path.join(
            temp_dir,
            "main.c"
        )

        executable_file = os.path.join(
            temp_dir,
            "main"
        )

        # Write C source
        with open(
            source_file,
            "w",
            encoding="utf-8"
        ) as file:
            file.write(code)

        # Compile
        compile_process = subprocess.run(
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

        compile_stdout = truncate_output(
            compile_process.stdout
        )

        compile_stderr = truncate_output(
            compile_process.stderr
        )

        # Compilation failed
        if compile_process.returncode != 0:

            return jsonify({
                "success": False,
                "stdout": compile_stdout,
                "stderr": compile_stderr,
                "exit_code": compile_process.returncode
            })

        # Run compiled C program
        result = execute_process(
            [
                executable_file
            ],
            stdin_text=stdin_text,
            cwd=temp_dir,
            timeout=EXECUTION_TIMEOUT
        )

        return jsonify({
            "success": (
                result["exit_code"] == 0
                and not result["timed_out"]
            ),
            "stdout": result["stdout"],
            "stderr": result["stderr"],
            "exit_code": result["exit_code"]
        })


# ============================================================
# RUN API
# ============================================================

@app.route("/api/run", methods=["POST"])
def run_code():

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

        # Normalize
        if code is None:
            code = ""

        if stdin_text is None:
            stdin_text = ""

        code = str(code)
        stdin_text = str(stdin_text)

        # Validate code
        valid, error = validate_code(code)

        if not valid:
            return jsonify({
                "success": False,
                "error": error
            }), 400

        # Validate stdin
        valid, error = validate_stdin(
            stdin_text
        )

        if not valid:
            return jsonify({
                "success": False,
                "error": error
            }), 400

        # Empty code
        if not code.strip():

            return jsonify({
                "success": False,
                "error": "Please enter some code first."
            }), 400

        # Python
        if language == "python":

            return execute_python(
                code,
                stdin_text
            )

        # JavaScript
        if language in (
            "javascript",
            "js"
        ):

            return execute_javascript(
                code,
                stdin_text
            )

        # SQL
        if language == "sql":

            return execute_sql(
                code
            )

        # C
        if language == "c":

            return execute_c(
                code,
                stdin_text
            )

        return jsonify({
            "success": False,
            "error": (
                "Unsupported language: "
                + language
            )
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
def check_runtimes():

    runtimes = {}

    commands = {
        "python": [
            "python3",
            "--version"
        ],

        "node": [
            "node",
            "--version"
        ],

        "gcc": [
            "gcc",
            "--version"
        ],

        "sqlite": [
            "sqlite3",
            "--version"
        ]
    }

    for name, command in commands.items():

        try:

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=3
            )

            output = (
                result.stdout
                or result.stderr
                or ""
            ).strip()

            if output:

                runtimes[name] = (
                    output.splitlines()[0]
                )

            else:

                runtimes[name] = "Unavailable"

        except Exception:

            runtimes[name] = "Unavailable"

    return jsonify(runtimes)


# ============================================================
# START SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
