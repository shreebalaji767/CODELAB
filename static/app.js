"use strict";


/* ============================================================
   CODE LAB
   ============================================================ */


const DEFAULT_CODE = {

    python:
`name = input("Your name: ")

print("Hello", name)

for i in range(1, 6):
    print("Number:", i)`,

    html:
`<!DOCTYPE html>
<html>

<head>
    <title>My Page</title>
</head>

<body>

    <h1>Hello CodeLab!</h1>

    <p>This is my HTML page.</p>

    <button onclick="alert('Hello!')">
        Click Me
    </button>

</body>

</html>`,

    css:
`body {
    font-family: Arial, sans-serif;
    padding: 30px;
    background: #f5f5f5;
}

h1 {
    color: #2563eb;
}

button {
    padding: 10px 18px;
    border: none;
    border-radius: 6px;
}`,

    javascript:
`console.log("Hello CodeLab!");

const name = "Shree";

console.log("Name:", name);

for (let i = 1; i <= 5; i++) {
    console.log("Number:", i);
}`,

    c:
`#include <stdio.h>

int main(void)
{
    char name[100];

    printf("Your name: ");

    if (scanf("%99s", name) != 1)
    {
        return 1;
    }

    printf("Hello %s!\\n", name);

    return 0;
}`
};


const LANGUAGE_NAMES = {

    python: "Python",

    html: "HTML",

    css: "CSS",

    javascript: "JavaScript",

    c: "C"
};


/* ============================================================
   ELEMENTS
   ============================================================ */

const language =
    document.getElementById("language");

const code =
    document.getElementById("code");

const stdin =
    document.getElementById("stdin");

const output =
    document.getElementById("output");

const preview =
    document.getElementById("preview");

const runButton =
    document.getElementById("run");

const resetButton =
    document.getElementById("reset");

const clearButton =
    document.getElementById("clear");

const status =
    document.getElementById("status");

const runtime =
    document.getElementById("runtime");


/* ============================================================
   CURRENT LANGUAGE
   ============================================================ */

let currentLanguage =
    language.value || "python";


/* ============================================================
   STORAGE
   ============================================================ */

function storageKey(name) {

    return "codelab_" + name;
}


function saveCurrentCode() {

    localStorage.setItem(
        storageKey(currentLanguage),
        code.value
    );
}


function loadCode(name) {

    const saved =
        localStorage.getItem(
            storageKey(name)
        );

    if (saved !== null) {

        code.value = saved;

    } else {

        code.value =
            DEFAULT_CODE[name] || "";
    }
}


/* ============================================================
   STATUS
   ============================================================ */

function setStatus(
    message,
    type = ""
) {

    status.textContent =
        message;

    status.className =
        "status";

    if (type) {

        status.classList.add(
            type
        );
    }
}


/* ============================================================
   OUTPUT
   ============================================================ */

function showOutput(text) {

    output.textContent =
        text || "";
}


function clearOutput() {

    output.textContent =
        "";

    setStatus(
        "Ready"
    );
}


/* ============================================================
   HTML
   ============================================================ */

function runHTML() {

    preview.srcdoc =
        code.value;

    showOutput(
        "HTML rendered successfully."
    );

    setStatus(
        "HTML preview updated",
        "success"
    );
}


/* ============================================================
   CSS
   ============================================================ */

function runCSS() {

    const css =
        code.value;

    const html =
`<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<style>

${css}

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

<div class="box">
Example Box
</div>

</body>

</html>`;

    preview.srcdoc =
        html;

    showOutput(
        "CSS rendered successfully."
    );

    setStatus(
        "CSS preview updated",
        "success"
    );
}


/* ============================================================
   JAVASCRIPT
   ============================================================ */

function runJavaScript() {

    const source =
        code.value;

    const messages = [];


    const customConsole = {

        log: function (...args) {

            messages.push(
                args
                    .map(formatValue)
                    .join(" ")
            );
        },

        info: function (...args) {

            messages.push(
                args
                    .map(formatValue)
                    .join(" ")
            );
        },

        warn: function (...args) {

            messages.push(
                "Warning: " +
                args
                    .map(formatValue)
                    .join(" ")
            );
        },

        error: function (...args) {

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
                    value
                );

            } catch {

                return String(
                    value
                );
            }
        }

        return String(
            value
        );
    }


    try {

        const execute =
            new Function(
                "console",
                source
            );

        execute(
            customConsole
        );


        if (
            messages.length === 0
        ) {

            showOutput(
                "JavaScript finished successfully."
            );

        } else {

            showOutput(
                messages.join("\n")
            );
        }


        setStatus(
            "JavaScript finished",
            "success"
        );

    } catch (error) {

        showOutput(
            error.name +
            ": " +
            error.message
        );

        setStatus(
            "JavaScript error",
            "error"
        );
    }
}


/* ============================================================
   PYTHON / C SERVER EXECUTION
   ============================================================ */

async function runServerLanguage() {

    const selectedLanguage =
        currentLanguage;

    const source =
        code.value;

    const input =
        stdin.value;


    setStatus(
        "Running..."
    );


    showOutput(
        "Running " +
        LANGUAGE_NAMES[
            selectedLanguage
        ] +
        "..."
    );


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
                            selectedLanguage,

                        code:
                            source,

                        stdin:
                            input
                    })
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            showOutput(
                data.error ||
                "Server request failed."
            );

            setStatus(
                "Error",
                "error"
            );

            return;
        }


        let result = "";


        if (data.stdout) {

            result +=
                data.stdout;
        }


        if (data.stderr) {

            if (result) {
                result += "\n";
            }

            result +=
                data.stderr;
        }


        if (!result) {

            if (data.success) {

                result =
                    "Program finished successfully.";

            } else {

                result =
                    "Program finished with an error.";
            }
        }


        showOutput(
            result
        );


        if (data.success) {

            setStatus(
                "Finished",
                "success"
            );

        } else {

            setStatus(
                "Program error",
                "error"
            );
        }

    } catch (error) {

        showOutput(
            "Could not connect to the CodeLab server.\n\n" +
            error.message
        );

        setStatus(
            "Connection error",
            "error"
        );
    }
}


/* ============================================================
   RUN
   ============================================================ */

async function runCode() {

    saveCurrentCode();


    if (
        currentLanguage ===
        "html"
    ) {

        runHTML();

        return;
    }


    if (
        currentLanguage ===
        "css"
    ) {

        runCSS();

        return;
    }


    if (
        currentLanguage ===
        "javascript"
    ) {

        runJavaScript();

        return;
    }


    if (
        currentLanguage ===
        "python" ||
        currentLanguage ===
        "c"
    ) {

        await runServerLanguage();

        return;
    }
}


/* ============================================================
   LANGUAGE CHANGE
   ============================================================ */

function changeLanguage() {

    saveCurrentCode();


    currentLanguage =
        language.value;


    loadCode(
        currentLanguage
    );


    showOutput(
        ""
    );


    setStatus(
        "Ready"
    );


    if (
        currentLanguage ===
        "html"
    ) {

        preview.srcdoc =
            code.value;

    } else if (
        currentLanguage ===
        "css"
    ) {

        runCSS();

    } else {

        preview.srcdoc =
`<!DOCTYPE html>

<html>

<body>

<h2>Browser Preview</h2>

<p>
HTML and CSS are displayed here.
</p>

</body>

</html>`;
    }
}


/* ============================================================
   RESET
   ============================================================ */

function resetCode() {

    code.value =
        DEFAULT_CODE[
            currentLanguage
        ] || "";


    saveCurrentCode();


    showOutput(
        ""
    );


    setStatus(
        "Code reset"
    );


    if (
        currentLanguage ===
        "html"
    ) {

        runHTML();

    } else if (
        currentLanguage ===
        "css"
    ) {

        runCSS();
    }
}


/* ============================================================
   CLEAR
   ============================================================ */

function clearCode() {

    code.value =
        "";

    saveCurrentCode();


    showOutput(
        ""
    );


    setStatus(
        "Editor cleared"
    );
}


/* ============================================================
   RUNTIME CHECK
   ============================================================ */

async function checkRuntime() {

    try {

        const response =
            await fetch(
                "/api/check"
            );


        const data =
            await response.json();


        runtime.textContent =
`Python: ${data.python || "Unavailable"}
GCC: ${data.gcc || "Unavailable"}`;

    } catch {

        runtime.textContent =
            "Runtime check unavailable.";
    }
}


/* ============================================================
   KEYBOARD
   ============================================================ */

function keyboardHandler(event) {

    if (
        event.ctrlKey &&
        event.key === "Enter"
    ) {

        event.preventDefault();

        runCode();
    }
}


/* ============================================================
   EVENTS
   ============================================================ */

language.addEventListener(
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


code.addEventListener(
    "input",
    saveCurrentCode
);


code.addEventListener(
    "keydown",
    keyboardHandler
);


/* ============================================================
   START
   ============================================================ */

function initialize() {

    currentLanguage =
        language.value || "python";

    loadCode(
        currentLanguage
    );

    setStatus(
        "Ready"
    );

    checkRuntime();
}


initialize();
