import os
import sys
import tempfile
import subprocess
import traceback
import resource
import signal

from flask import Flask, jsonify, render_template, request


app = Flask(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

PORT = int(os.environ.get("PORT", "10000"))

MAX_CODE_BYTES = 100 * 1024
MAX_INPUT_BYTES = 50 * 1024
MAX_OUTPUT_BYTES = 100 * 1024

COMPILE_TIMEOUT = 10
RUN_TIMEOUT = 5


# ============================================================
# RESOURCE LIMITS
# ============================================================

def apply_resource_limits():
    """
    Linux process limits.

    These provide basic protection against programs that consume
    excessive CPU, memory, output, files, or processes.

    This is NOT a complete security sandbox.
    """

    try:
        # CPU seconds
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (RUN_TIMEOUT, RUN_TIMEOUT + 1)
        )
    except Exception:
        pass

    try:
        # Maximum address space: 256 MB
        memory_limit = 256 * 1024 * 1024

        resource.setrlimit(
            resource.RLIMIT_AS,
            (memory_limit, memory_limit)
        )
    except Exception:
        pass

    try:
        # Maximum generated file size: 10 MB
        file_limit = 10 * 1024 * 1024

        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (file_limit, file_limit)
        )
    except Exception:
        pass

    try:
        # Maximum number of child processes
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (32, 32)
        )
    except Exception:
        pass

    try:
        # Maximum number of open files
        resource.setrlimit(
            resource.RLIMIT_NOFILE,
            (64, 64)
        )
    except Exception:
        pass


# ============================================================
# OUTPUT HELPERS
# ============================================================

def decode_output(value):
    if value is None:
        return ""

    if isinstance(value, bytes):
        value = value.decode(
            "utf-8",
            errors="replace"
        )

    return str(value)


def limit_output(value):
    value = decode_output(value)

    if len(value) > MAX_OUTPUT_BYTES:

        return (
            value[:MAX_OUTPUT_BYTES]
            + "\n\n"
            + "[Output truncated because it exceeded "
              "the maximum output size.]"
        )

    return value


# ============================================================
# VALIDATION
# ============================================================

def validate_text(
    code,
    stdin_text
):

    if not isinstance(code, str):
        return False, "Invalid code."

    if not isinstance(stdin_text, str):
        return False, "Invalid input."

    if len(code.encode("utf-8")) > MAX_CODE_BYTES:

        return (
            False,
            "Code is too large. Maximum size is 100 KB."
        )

    if len(stdin_text.encode("utf-8")) > MAX_INPUT_BYTES:

        return (
            False,
            "Input is too large. Maximum size is 50 KB."
        )

    if not code.strip():

        return (
            False,
            "Please enter some code."
        )

    return True, ""


# ============================================================
# PROCESS EXECUTION
# ============================================================

def run_process(
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
            preexec_fn=apply_resource_limits
        )

        stdout = limit_output(
            process.stdout
        )

        stderr = limit_output(
            process.stderr
        )

        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": process.returncode,
            "timeout": False,
            "success": process.returncode == 0
        }

    except subprocess.TimeoutExpired as error:

        stdout = limit_output(
            error.stdout
        )

        stderr = limit_output(
            error.stderr
        )

        message = (
            "Program execution timed out after "
            f"{timeout} seconds."
        )

        if stderr:
            stderr += "\n\n"

        stderr += message

        return {
            "stdout": stdout,
            "stderr": stderr,
            "returncode": -1,
            "timeout": True,
            "success": False
        }

    except MemoryError:

        return {
            "stdout": "",
            "stderr": "Program exceeded the memory limit.",
            "returncode": -1,
            "timeout": False,
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
# PYTHON COMPILER
# ============================================================

def run_python(code, stdin_text):

    result = run_process(
        [
            sys.executable,
            "-I",
            "-u",
            "-c",
            code
        ],
        stdin_text=stdin_text,
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


# ============================================================
# C COMPILER
# ============================================================

def run_c(code, stdin_text):

    with tempfile.TemporaryDirectory(
        prefix="codelab_"
    ) as temp_dir:

        source_file = os.path.join(
            temp_dir,
            "main.c"
        )

        executable_file = os.path.join(
            temp_dir,
            "program"
        )

        # ----------------------------------------------------
        # WRITE SOURCE
        # ----------------------------------------------------

        try:

            with open(
                source_file,
                "w",
                encoding="utf-8"
            ) as source:

                source.write(code)

        except Exception as error:

            return jsonify({
                "success": False,
                "language": "c",
                "phase": "source",
                "stdout": "",
                "stderr": (
                    "Could not create C source file.\n\n"
                    + str(error)
                ),
                "returncode": -1,
                "timeout": False
            })


        # ----------------------------------------------------
        # COMPILE
        # ----------------------------------------------------

        try:

            compile_process = subprocess.run(
                [
                    "gcc",
                    "-std=c17",
                    "-O0",
                    "-Wall",
                    "-Wextra",
                    "-Wpedantic",
                    "-fno-asm",
                    source_file,
                    "-o",
                    executable_file
                ],
                capture_output=True,
                text=True,
                cwd=temp_dir,
                timeout=COMPILE_TIMEOUT,
                preexec_fn=apply_resource_limits
            )

        except subprocess.TimeoutExpired:

            return jsonify({
                "success": False,
                "language": "c",
                "phase": "compile",
                "stdout": "",
                "stderr": (
                    "C compilation timed out after "
                    f"{COMPILE_TIMEOUT} seconds."
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


        # ----------------------------------------------------
        # COMPILER ERROR
        # ----------------------------------------------------

        if compile_process.returncode != 0:

            return jsonify({
                "success": False,
                "language": "c",
                "phase": "compile",
                "stdout": limit_output(
                    compile_process.stdout
                ),
                "stderr": limit_output(
                    compile_process.stderr
                ),
                "returncode": compile_process.returncode,
                "timeout": False
            })


        # ----------------------------------------------------
        # EXECUTE PROGRAM
        # ----------------------------------------------------

        result = run_process(
            [
                executable_file
            ],
            stdin_text=stdin_text,
            cwd=temp_dir,
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


# ============================================================
# MAIN API
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
                "error": "Invalid JSON request."
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


        valid, message = validate_text(
            code,
            stdin_text
        )


        if not valid:

            return jsonify({
                "success": False,
                "error": message
            }), 400


        # ----------------------------------------------------
        # PYTHON
        # ----------------------------------------------------

        if language == "python":

            return run_python(
                code,
                stdin_text
            )


        # ----------------------------------------------------
        # C
        # ----------------------------------------------------

        if language == "c":

            return run_c(
                code,
                stdin_text
            )


        # ----------------------------------------------------
        # FRONTEND LANGUAGES
        # ----------------------------------------------------

        if language in [
            "html",
            "css",
            "javascript"
        ]:

            return jsonify({
                "success": False,
                "error": (
                    language.capitalize()
                    + " runs in the browser. "
                      "It should not be sent to the "
                      "server compiler."
                )
            }), 400


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
            "error": (
                type(error).__name__
                + ": "
                + str(error)
            ),
            "traceback": traceback.format_exc()
        }), 500


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
# RUNTIME CHECK
# ============================================================

@app.route("/api/runtime")
def runtime():

    python_version = ""
    gcc_version = ""
    gcc_available = False

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


    return jsonify({

        "python": python_version,

        "gcc": gcc_version,

        "gcc_available": gcc_available,

        "python_executable":
            sys.executable

    })


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False
    )
