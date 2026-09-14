import os
import sys
import tempfile
import subprocess
import traceback
import resource

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

PORT = int(os.environ.get("PORT", "10000"))

MAX_CODE_BYTES = 100 * 1024
MAX_INPUT_BYTES = 50 * 1024
MAX_OUTPUT_BYTES = 100 * 1024

COMPILE_TIMEOUT = 10
RUN_TIMEOUT = 5


def apply_limits():
    try:
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (RUN_TIMEOUT, RUN_TIMEOUT + 1)
        )
    except Exception:
        pass

    try:
        memory = 256 * 1024 * 1024
        resource.setrlimit(
            resource.RLIMIT_AS,
            (memory, memory)
        )
    except Exception:
        pass

    try:
        file_limit = 10 * 1024 * 1024
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (file_limit, file_limit)
        )
    except Exception:
        pass

    try:
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (32, 32)
        )
    except Exception:
        pass

    try:
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (64, 64)
        )
    except Exception:
        pass


def clean_output(value):
    if value is None:
        return ""

    if isinstance(value, bytes):
        value = value.decode(
            "utf-8",
            errors="replace"
        )

    value = str(value)

    if len(value) > MAX_OUTPUT_BYTES:
        return (
            value[:MAX_OUTPUT_BYTES]
            + "\n\n"
            + "[Output truncated.]"
        )

    return value


def validate(code, stdin_text):
    if not isinstance(code, str):
        return False, "Invalid code."

    if not isinstance(stdin_text, str):
        return False, "Invalid input."

    if len(code.encode("utf-8")) > MAX_CODE_BYTES:
        return (
            False,
            "Code is too large. Maximum is 100 KB."
        )

    if len(stdin_text.encode("utf-8")) > MAX_INPUT_BYTES:
        return (
            False,
            "Input is too large. Maximum is 50 KB."
        )

    if not code.strip():
        return False, "Please enter some code."

    return True, ""


def execute(
    command,
    stdin_text,
    cwd=None,
    timeout=RUN_TIMEOUT
):
    try:
        process = subprocess.run(
            command,
            input=stdin_text,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout,
            preexec_fn=apply_limits
        )

        return {
            "stdout": clean_output(
                process.stdout
            ),
            "stderr": clean_output(
                process.stderr
            ),
            "returncode": process.returncode,
            "timeout": False,
            "success": process.returncode == 0
        }

    except subprocess.TimeoutExpired as error:

        stderr = clean_output(
            error.stderr
        )

        if stderr:
            stderr += "\n\n"

        stderr += (
            "Program execution timed out after "
            f"{timeout} seconds."
        )

        return {
            "stdout": clean_output(
                error.stdout
            ),
            "stderr": stderr,
            "returncode": -1,
            "timeout": True,
            "success": False
        }

    except Exception as error:

        return {
            "stdout": "",
            "stderr": (
                type(error).__name__
                + ": "
                + str(error)
            ),
            "returncode": -1,
            "timeout": False,
            "success": False
        }


# ============================================================
# HOME PAGE
# ============================================================

@app.route("/")
def index():
    return render_template(
        "index.html"
    )


# ============================================================
# HEALTH
# ============================================================

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "CodeLab"
    })


# ============================================================
# RUNTIME INFORMATION
# ============================================================

@app.route("/api/runtime")
def runtime():

    try:
        python_result = subprocess.run(
            [
                sys.executable,
                "--version"
            ],
            capture_output=True,
            text=True,
            timeout=3
        )

        python_version = (
            python_result.stdout
            or python_result.stderr
        ).strip()

    except Exception as error:

        python_version = (
            "Unavailable: "
            + str(error)
        )

    try:
        gcc_result = subprocess.run(
            [
                "gcc",
                "--version"
            ],
            capture_output=True,
            text=True,
            timeout=3
        )

        gcc_version = (
            gcc_result.stdout
            or gcc_result.stderr
        ).strip()

        gcc_available = (
            gcc_result.returncode == 0
        )

    except Exception as error:

        gcc_version = (
            "Unavailable: "
            + str(error)
        )

        gcc_available = False

    return jsonify({
        "python": python_version,
        "gcc": gcc_version,
        "gcc_available": gcc_available
    })


# ============================================================
# RUN API
# ============================================================

@app.route(
    "/api/run",
    methods=["POST"]
)
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
            data.get(
                "language",
                ""
            )
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

        valid, message = validate(
            code,
            stdin_text
        )

        if not valid:

            return jsonify({
                "success": False,
                "error": message
            }), 400


        # ====================================================
        # PYTHON
        # ====================================================

        if language == "python":

            result = execute(
                [
                    sys.executable,
                    "-I",
                    "-u",
                    "-c",
                    code
                ],
                stdin_text,
                timeout=RUN_TIMEOUT
            )

            return jsonify({
                "success": result["success"],
                "language": "python",
                "phase": "run",
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "returncode": result["returncode"],
                "timeout": result["timeout"]
            })


        # ====================================================
        # C
        # ====================================================

        if language == "c":

            with tempfile.TemporaryDirectory(
                prefix="codelab_"
            ) as temp:

                source_file = os.path.join(
                    temp,
                    "main.c"
                )

                binary_file = os.path.join(
                    temp,
                    "program"
                )

                try:

                    with open(
                        source_file,
                        "w",
                        encoding="utf-8"
                    ) as file:

                        file.write(code)

                except Exception as error:

                    return jsonify({
                        "success": False,
                        "language": "c",
                        "phase": "source",
                        "stdout": "",
                        "stderr": (
                            "Could not create C "
                            "source file.\n\n"
                            + str(error)
                        ),
                        "returncode": -1,
                        "timeout": False
                    })


                # --------------------------------------------
                # COMPILE
                # --------------------------------------------

                try:

                    compile_result = subprocess.run(
                        [
                            "gcc",
                            "-std=c17",
                            "-O0",
                            "-Wall",
                            "-Wextra",
                            "-Wpedantic",
                            source_file,
                            "-o",
                            binary_file
                        ],
                        capture_output=True,
                        text=True,
                        cwd=temp,
                        timeout=COMPILE_TIMEOUT,
                        preexec_fn=apply_limits
                    )

                except subprocess.TimeoutExpired:

                    return jsonify({
                        "success": False,
                        "language": "c",
                        "phase": "compile",
                        "stdout": "",
                        "stderr": (
                            "C compilation timed out "
                            f"after {COMPILE_TIMEOUT} seconds."
                        ),
                        "returncode": -1,
                        "timeout": True
                    })

                except Exception as error:

                    return jsonify({
                        "success": False,
                        "language": "c",
                        "phase": "compile",
                        "stdout": "",
                        "stderr": (
                            type(error).__name__
                            + ": "
                            + str(error)
                        ),
                        "returncode": -1,
                        "timeout": False
                    })


                # --------------------------------------------
                # COMPILATION ERROR
                # --------------------------------------------

                if compile_result.returncode != 0:

                    return jsonify({
                        "success": False,
                        "language": "c",
                        "phase": "compile",
                        "stdout": clean_output(
                            compile_result.stdout
                        ),
                        "stderr": clean_output(
                            compile_result.stderr
                        ),
                        "returncode": (
                            compile_result.returncode
                        ),
                        "timeout": False
                    })


                # --------------------------------------------
                # RUN C PROGRAM
                # --------------------------------------------

                result = execute(
                    [
                        binary_file
                    ],
                    stdin_text,
                    cwd=temp,
                    timeout=RUN_TIMEOUT
                )

                return jsonify({
                    "success": result["success"],
                    "language": "c",
                    "phase": "run",
                    "stdout": result["stdout"],
                    "stderr": result["stderr"],
                    "returncode": result["returncode"],
                    "timeout": result["timeout"]
                })


        return jsonify({
            "success": False,
            "error": (
                "Unsupported server language: "
                + language
            )
        }), 400


    except Exception as error:

        return jsonify({
            "success": False,
            "error": (
                type(error).__name__
                + ": "
                + str(error)
            ),
            "traceback": traceback.format_exc()
        }), 500


# ============================================================
# SERVER
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
