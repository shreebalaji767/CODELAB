"use strict";


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
    <title>CodeLab</title>
</head>

<body>

    <h1>Hello CodeLab!</h1>

    <p>This is HTML.</p>

</body>

</html>`,

    css:
`body {
    font-family: Arial, sans-serif;
    padding: 30px;
}

h1 {
    color: #2563eb;
}

p {
    font-size: 18px;
}`,

    javascript:
`console.log("Hello CodeLab!");

let a = 10;
let b = 20;

console.log("Answer:", a + b);`,

    c:
`#include <stdio.h>

int main(void)
{
    int age;

    printf("Enter your age: ");

    scanf("%d", &age);

    printf("Your age is %d\\n", age);

    return 0;
}`
};


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


let currentLanguage =
    language.value || "python";


function storageKey(languageName) {

    return "codelab_" + languageName;
}


function loadCode(languageName) {

    const saved =
        localStorage.getItem(
            storageKey(languageName)
        );

    if (saved !== null) {

        code.value = saved;

    } else {

        code.value =
            DEFAULT_CODE[languageName] || "";
    }
}


function saveCode() {

    localStorage.setItem(
        storageKey(currentLanguage),
        code.value
    );
}


function setStatus(
    message,
    type = ""
) {

    status.textContent =
        message;

    status.className =
        "status";

    if (type) {

        status.classList.add(type);
    }
}


function showOutput(text) {

    output.textContent =
        text || "";
}


/* ============================================================
   HTML
   ============================================================ */

function runHTML() {

    preview.srcdoc =
        code.value;

    showOutput(
        "HTML preview updated."
    );

    setStatus(
        "HTML ready",
        "success"
    );
}


/* ============================================================
   CSS
   ============================================================ */

function runCSS() {

    const html =
`<!DOCTYPE html>

<html>

<head>

<meta charset="UTF-8">

<style>

${code.value}

</style>

</head>

<body>

<h1>CSS Preview</h1>

<p>This page is using your CSS.</p>

<button>Example Button</button>

</body>

</html>`;

    preview.srcdoc =
        html;

    showOutput(
        "CSS preview updated."
    );

    setStatus(
        "CSS ready",
        "success"
    );
}


/* ============================================================
   JAVASCRIPT
   ============================================================ */

function runJavaScript() {

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

        return String(value);
    }


    try {

        const execute =
            new Function(
                "console",
                code.value
            );

        execute(
            customConsole
        );

        if (messages.length === 0) {

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
   PYTHON + C
   ============================================================ */

async function runServerLanguage() {

    setStatus(
        "Running..."
    );

    showOutput(
        "Running " +
        currentLanguage +
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
                            currentLanguage,

                        code:
                            code.value,

                        stdin:
                            stdin.value
                    })
                }
            );


        const data =
            await response.json();


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


        if (data.error) {

            if (result) {
                result += "\n\n";
            }

            result +=
                data.error;
        }


        if (!result) {

            result =
                data.success
                    ? "Program finished successfully."
                    : "Program failed.";
        }


        showOutput(
            result
        );


        if (
            response.ok &&
            data.success
        ) {

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
            "CONNECTION ERROR\n\n" +
            error.name +
            ": " +
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

    saveCode();


    if (
        currentLanguage === "html"
    ) {

        runHTML();

        return;
    }


    if (
        currentLanguage === "css"
    ) {

        runCSS();

        return;
    }


    if (
        currentLanguage === "javascript"
    ) {

        runJavaScript();

        return;
    }


    if (
        currentLanguage === "python" ||
        currentLanguage === "c"
    ) {

        await runServerLanguage();

        return;
    }
}


/* ============================================================
   LANGUAGE CHANGE
   ============================================================ */

function changeLanguage() {

    saveCode();

    currentLanguage =
        language.value;

    loadCode(
        currentLanguage
    );

    showOutput("");

    setStatus(
        "Ready"
    );


    if (
        currentLanguage === "html"
    ) {

        preview.srcdoc =
            code.value;

    } else if (
        currentLanguage === "css"
    ) {

        runCSS();

    } else {

        preview.srcdoc =
`<!DOCTYPE html>

<html>

<body>

<h2>Browser Preview</h2>

<p>
HTML and CSS preview appears here.
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

    saveCode();

    showOutput("");

    setStatus(
        "Code reset"
    );


    if (
        currentLanguage === "html"
    ) {

        runHTML();

    } else if (
        currentLanguage === "css"
    ) {

        runCSS();
    }
}


/* ============================================================
   CLEAR
   ============================================================ */

function clearCode() {

    code.value = "";

    saveCode();

    showOutput("");

    setStatus(
        "Editor cleared"
    );
}


/* ============================================================
   RUNTIME
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
    saveCode
);


code.addEventListener(
    "keydown",
    function(event) {

        if (
            event.ctrlKey &&
            event.key === "Enter"
        ) {

            event.preventDefault();

            runCode();
        }
    }
);


/* ============================================================
   INITIALIZE
   ============================================================ */

loadCode(
    currentLanguage
);

setStatus(
    "Ready"
);

checkRuntime();
