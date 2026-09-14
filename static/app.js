"use strict";


/* ============================================================
   DEFAULT PROGRAMS
   ============================================================ */

const DEFAULT_CODE = {

    html:
`<!DOCTYPE html>
<html>
<head>
    <title>CodeLab</title>
</head>

<body>

    <h1>Hello CodeLab!</h1>

    <p>This is an HTML program.</p>

</body>
</html>`,



    css:
`body {
    font-family: Arial, sans-serif;
    padding: 30px;
}

h1 {
    color: #04aa6d;
}

p {
    font-size: 18px;
}`,



    javascript:
`console.log("Hello from JavaScript!");

let a = 10;
let b = 20;

console.log("Answer:", a + b);`,



    python:
`name = input("Enter your name: ")

print("Hello,", name)

for i in range(1, 6):
    print("Number:", i)`,



    c:
`#include <stdio.h>

int main(void)
{
    char name[100];
    int age;

    printf("Enter your name: ");
    scanf("%99s", name);

    printf("Enter your age: ");
    scanf("%d", &age);

    printf("\\nHello %s!\\n", name);
    printf("You are %d years old.\\n", age);

    return 0;
}`
};


/* ============================================================
   ELEMENTS
   ============================================================ */

const languageSelect =
    document.getElementById(
        "language"
    );


const codeEditor =
    document.getElementById(
        "code"
    );


const stdinEditor =
    document.getElementById(
        "stdin"
    );


const output =
    document.getElementById(
        "output"
    );


const preview =
    document.getElementById(
        "preview"
    );


const runButton =
    document.getElementById(
        "run-button"
    );


const resetButton =
    document.getElementById(
        "reset-button"
    );


const clearButton =
    document.getElementById(
        "clear-button"
    );


const languageLabel =
    document.getElementById(
        "language-label"
    );


const resultStatus =
    document.getElementById(
        "result-status"
    );


const inputContainer =
    document.getElementById(
        "input-container"
    );


const serverStatus =
    document.getElementById(
        "server-status"
    );


const runtimeInfo =
    document.getElementById(
        "runtime-info"
    );


/* ============================================================
   LOCAL STORAGE
   ============================================================ */

function storageKey(language) {

    return (
        "codelab_code_" +
        language
    );
}


function saveCurrentCode() {

    localStorage.setItem(
        storageKey(
            languageSelect.value
        ),
        codeEditor.value
    );
}


function loadCode(language) {

    const saved =
        localStorage.getItem(
            storageKey(language)
        );


    if (saved !== null) {

        codeEditor.value =
            saved;

    } else {

        codeEditor.value =
            DEFAULT_CODE[language] || "";
    }
}


/* ============================================================
   UI STATUS
   ============================================================ */

function setResultStatus(
    text,
    type = ""
) {

    resultStatus.textContent =
        text;

    resultStatus.className =
        "result-status";


    if (type) {

        resultStatus.classList.add(
            type
        );
    }
}


function setOutput(text) {

    output.textContent =
        text || "";
}


/* ============================================================
   LANGUAGE MODE
   ============================================================ */

function updateLanguageUI() {

    const language =
        languageSelect.value;


    languageLabel.textContent =
        language.toUpperCase();


    if (
        language === "python" ||
        language === "c"
    ) {

        inputContainer.classList.remove(
            "hidden"
        );

    } else {

        inputContainer.classList.add(
            "hidden"
        );
    }
}


/* ============================================================
   HTML
   ============================================================ */

function runHTML() {

    preview.srcdoc =
        codeEditor.value;


    setOutput(
        "HTML preview updated."
    );


    setResultStatus(
        "Ready",
        "success"
    );
}


/* ============================================================
   CSS
   ============================================================ */

function runCSS() {

    const documentHTML =
`<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<style>

${codeEditor.value}

</style>

</head>

<body>

<h1>CSS Preview</h1>

<p>
This page is using your CSS.
</p>

<button>
Example Button
</button>

</body>

</html>`;


    preview.srcdoc =
        documentHTML;


    setOutput(
        "CSS preview updated."
    );


    setResultStatus(
        "Ready",
        "success"
    );
}


/* ============================================================
   JAVASCRIPT
   ============================================================ */

function runJavaScript() {

    const messages = [];


    const customConsole = {

        log(...args) {

            messages.push(
                args
                    .map(formatValue)
                    .join(" ")
            );
        },


        info(...args) {

            messages.push(
                args
                    .map(formatValue)
                    .join(" ")
            );
        },


        warn(...args) {

            messages.push(
                "Warning: " +
                args
                    .map(formatValue)
                    .join(" ")
            );
        },


        error(...args) {

            messages.push(
                "Error: " +
                args
                    .map(formatValue)
                    .join(" ")
            );
        }
    };


    function formatValue(value) {

        if (
            value === undefined
        ) {

            return "undefined";
        }


        if (
            value === null
        ) {

            return "null";
        }


        if (
            typeof value === "object"
        ) {

            try {

                return JSON.stringify(
                    value,
                    null,
                    2
                );

            } catch {

                return String(
                    value
                );
            }
        }


        return String(value);
    }


    try {

        const execute =
            new Function(
                "console",
                codeEditor.value
            );


        execute(
            customConsole
        );


        if (
            messages.length === 0
        ) {

            setOutput(
                "JavaScript finished successfully."
            );

        } else {

            setOutput(
                messages.join("\n")
            );
        }


        setResultStatus(
            "Finished",
            "success"
        );


    } catch (error) {

        setOutput(
            error.name +
            ": " +
            error.message
        );


        setResultStatus(
            "Error",
            "error"
        );
    }
}


/* ============================================================
   PYTHON / C API
   ============================================================ */

async function runCompiler() {

    const language =
        languageSelect.value;


    setResultStatus(
        "Running...",
        "running"
    );


    setOutput(
        "Running " +
        language +
        "..."
    );


    runButton.disabled =
        true;


    try {

        const response =
            await fetch(
                "/api/run",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        language:
                            language,

                        code:
                            codeEditor.value,

                        stdin:
                            stdinEditor.value
                    })
                }
            );


        const data =
            await response.json();


        let result = "";


        /* ----------------------------------------------------
           STDOUT
           ---------------------------------------------------- */

        if (
            data.stdout
        ) {

            result +=
                data.stdout;
        }


        /* ----------------------------------------------------
           STDERR
           ---------------------------------------------------- */

        if (
            data.stderr
        ) {

            if (result) {

                result +=
                    "\n";
            }


            result +=
                data.stderr;
        }


        /* ----------------------------------------------------
           API ERROR
           ---------------------------------------------------- */

        if (
            data.error
        ) {

            if (result) {

                result +=
                    "\n\n";
            }


            result +=
                data.error;
        }


        /* ----------------------------------------------------
           EMPTY RESULT
           ---------------------------------------------------- */

        if (!result) {

            if (
                data.success
            ) {

                result =
                    "Program finished successfully.";
            } else {

                result =
                    "Program failed.";
            }
        }


        /* ----------------------------------------------------
           DISPLAY
           ---------------------------------------------------- */

        setOutput(
            result
        );


        /* ----------------------------------------------------
           STATUS
           ---------------------------------------------------- */

        if (
            data.timeout
        ) {

            setResultStatus(
                "Timeout",
                "error"
            );

        } else if (
            data.phase === "compile"
        ) {

            setResultStatus(
                data.success
                    ? "Compiled"
                    : "Compilation Error",
                data.success
                    ? "success"
                    : "error"
            );

        } else if (
            data.success
        ) {

            setResultStatus(
                "Finished",
                "success"
            );

        } else {

            setResultStatus(
                "Runtime Error",
                "error"
            );
        }


    } catch (error) {

        setOutput(
`Could not connect to the CodeLab compiler.

${error.name}: ${error.message}

Check that the Render deployment is running.`
        );


        setResultStatus(
            "Server Error",
            "error"
        );

    } finally {

        runButton.disabled =
            false;
    }
}


/* ============================================================
   MAIN RUN
   ============================================================ */

async function runCode() {

    saveCurrentCode();


    const language =
        languageSelect.value;


    if (
        language === "html"
    ) {

        runHTML();

        return;
    }


    if (
        language === "css"
    ) {

        runCSS();

        return;
    }


    if (
        language === "javascript"
    ) {

        runJavaScript();

        return;
    }


    if (
        language === "python" ||
        language === "c"
    ) {

        await runCompiler();

        return;
    }


    setOutput(
        "Unsupported language."
    );


    setResultStatus(
        "Error",
        "error"
    );
}


/* ============================================================
   LANGUAGE CHANGE
   ============================================================ */

function changeLanguage() {

    saveCurrentCode();


    const language =
        languageSelect.value;


    loadCode(
        language
    );


    updateLanguageUI();


    setOutput(
        ""
    );


    setResultStatus(
        "Ready"
    );


    if (
        language === "html"
    ) {

        preview.srcdoc =
            codeEditor.value;

    } else if (
        language === "css"
    ) {

        runCSS();

    } else {

        preview.srcdoc =
`<!DOCTYPE html>

<html>

<body style="
    font-family: Arial;
    padding: 20px;
">

<h2>
Browser Preview
</h2>

<p>
HTML/CSS preview appears here.
</p>

</body>

</html>`;
    }
}


/* ============================================================
   RESET
   ============================================================ */

function resetCode() {

    const language =
        languageSelect.value;


    codeEditor.value =
        DEFAULT_CODE[language] || "";


    saveCurrentCode();


    setOutput(
        ""
    );


    setResultStatus(
        "Reset"
    );


    if (
        language === "html"
    ) {

        runHTML();

    } else if (
        language === "css"
    ) {

        runCSS();
    }
}


/* ============================================================
   CLEAR
   ============================================================ */

function clearCode() {

    codeEditor.value =
        "";


    saveCurrentCode();


    setOutput(
        ""
    );


    setResultStatus(
        "Ready"
    );
}


/* ============================================================
   SERVER CHECK
   ============================================================ */

async function checkServer() {

    try {

        const response =
            await fetch(
                "/health",
                {
                    cache: "no-store"
                }
            );


        if (
            response.ok
        ) {

            serverStatus.textContent =
                "● Server Online";

            serverStatus.style.color =
                "#04aa6d";

        } else {

            throw new Error(
                "Server unavailable"
            );
        }


    } catch {

        serverStatus.textContent =
            "● Server Offline";

        serverStatus.style.color =
            "#e74c3c";
    }
}


/* ============================================================
   RUNTIME CHECK
   ============================================================ */

async function checkRuntime() {

    try {

        const response =
            await fetch(
                "/api/runtime",
                {
                    cache: "no-store"
                }
            );


        const data =
            await response.json();


        const python =
            data.python ||
            "Python unavailable";


        const gcc =
            data.gcc ||
            "GCC unavailable";


        const pythonShort =
            python
                .split("\n")[0];


        const gccShort =
            gcc
                .split("\n")[0];


        runtimeInfo.textContent =
            pythonShort +
            " | " +
            gccShort;


        if (
            data.gcc_available
        ) {

            serverStatus.textContent =
                "● Compiler Ready";

            serverStatus.style.color =
                "#04aa6d";
        }


    } catch {

        runtimeInfo.textContent =
            "Runtime information unavailable.";
    }
}


/* ============================================================
   KEYBOARD SHORTCUT
   ============================================================ */

codeEditor.addEventListener(
    "keydown",
    function(event) {

        if (
            event.ctrlKey &&
            event.key === "Enter"
        ) {

            event.preventDefault();

            runCode();
        }


        /*
         * Make Tab insert spaces instead of
         * moving focus away from the editor.
         */

        if (
            event.key === "Tab"
        ) {

            event.preventDefault();


            const start =
                codeEditor.selectionStart;


            const end =
                codeEditor.selectionEnd;


            codeEditor.value =
                codeEditor.value.substring(
                    0,
                    start
                )
                +
                "    "
                +
                codeEditor.value.substring(
                    end
                );


            codeEditor.selectionStart =
                start + 4;


            codeEditor.selectionEnd =
                start + 4;


            saveCurrentCode();
        }
    }
);


/* ============================================================
   INPUT EVENTS
   ============================================================ */

codeEditor.addEventListener(
    "input",
    function() {

        saveCurrentCode();
    }
);


/* ============================================================
   BUTTON EVENTS
   ============================================================ */

languageSelect.addEventListener(
    "change",
    changeLanguage
);


runButton.addEventListener(
    "click",
    runCode
);


resetButton.addEventListener(
    "click",
    resetCode
);


clearButton.addEventListener(
    "click",
    clearCode
);


/* ============================================================
   INITIALIZE
   ============================================================ */

loadCode(
    languageSelect.value
);


updateLanguageUI();


checkServer();


checkRuntime();
