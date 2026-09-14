const languageSelect =
    document.getElementById("language");

const codeBox =
    document.getElementById("code");

const inputBox =
    document.getElementById("input");

const resultBox =
    document.getElementById("result");

const runButton =
    document.getElementById("runButton");

const resetButton =
    document.getElementById("resetButton");

const clearButton =
    document.getElementById("clearButton");

const languageBadge =
    document.getElementById("languageBadge");

const statusBox =
    document.getElementById("status");

const preview =
    document.getElementById("preview");

const previewPanel =
    document.getElementById("previewPanel");

const openPreviewButton =
    document.getElementById("openPreviewButton");

const runtimeStatus =
    document.getElementById("runtimeStatus");


/* ========================================================
   EXAMPLES
   ======================================================== */

const examples = {

    html:
`<h1>Hello CodeLab!</h1>
<p>This is an HTML example.</p>`,

    css:
`body {
    font-family: Arial;
    background: lightblue;
}

h1 {
    color: darkblue;
}`,

    javascript:
`console.log("Hello from JavaScript!");

const name = prompt("What is your name?");

console.log("Hello " + name);`,

    python:
`name = input("Enter your name: ")
print("Hello", name)`,

    c:
`#include <stdio.h>

int main() {

    int age;

    printf("Enter your age: ");

    scanf("%d", &age);

    printf("Your age is %d\\n", age);

    return 0;
}`
};


/* ========================================================
   LANGUAGE
   ======================================================== */

function currentLanguage() {

    return languageSelect.value;

}


/* ========================================================
   STATUS
   ======================================================== */

function setStatus(
    text,
    type = ""
) {

    statusBox.textContent = text;

    statusBox.className = "status";

    if (type) {

        statusBox.classList.add(
            type
        );

    }

}


/* ========================================================
   LOAD EXAMPLE
   ======================================================== */

function loadExample() {

    const language =
        currentLanguage();

    codeBox.value =
        examples[language] || "";

    inputBox.value = "";

    resultBox.textContent = "";

    languageBadge.textContent =
        language === "javascript"
            ? "JavaScript"
            : language.charAt(0).toUpperCase()
              + language.slice(1);

    setStatus("Ready");


    if (
        language === "html" ||
        language === "css" ||
        language === "javascript"
    ) {

        previewPanel.style.display =
            "block";

        renderBrowserCode();

    }

    else {

        previewPanel.style.display =
            "none";

        preview.srcdoc = "";

    }

}


/* ========================================================
   BROWSER CODE
   ======================================================== */

function renderBrowserCode() {

    const language =
        currentLanguage();

    const code =
        codeBox.value;


    /* HTML */

    if (language === "html") {

        preview.srcdoc =
            code;

        return;

    }


    /* CSS */

    if (language === "css") {

        preview.srcdoc = `
<!DOCTYPE html>

<html>

<head>

<style>

${code}

</style>

</head>

<body>

<h1>CSS Preview</h1>

<p>
Edit the CSS code to see the result.
</p>

<button>
Example Button
</button>

</body>

</html>
`;

        return;

    }


    /* JavaScript */

    if (language === "javascript") {

        const safeCode =
            code.replace(
                /<\/script/gi,
                "<\\/script"
            );

        preview.srcdoc = `
<!DOCTYPE html>

<html>

<body>

<h2>
JavaScript Preview
</h2>

<p>
Open the browser console to see
console.log output.
</p>

<script>

try {

${safeCode}

}

catch (error) {

document.body.insertAdjacentHTML(
    "beforeend",
    "<pre style='color:red;white-space:pre-wrap'>" +
    error.stack +
    "</pre>"
);

}

<\/script>

</body>

</html>
`;

    }

}


/* ========================================================
   SERVER CODE
   ======================================================== */

async function runServerCode() {

    const language =
        currentLanguage();

    setStatus(
        "Running..."
    );

    resultBox.textContent =
        "";

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
                        language: language,

                        code:
                            codeBox.value,

                        stdin:
                            inputBox.value
                    })
                }
            );


        const text =
            await response.text();


        let data;


        try {

            data =
                JSON.parse(text);

        }

        catch {

            throw new Error(
                "Server returned HTTP "
                + response.status
                + " instead of JSON.\n\n"
                + text
            );

        }


        if (!response.ok) {

            throw new Error(
                data.error ||
                data.stderr ||
                "Server error: HTTP "
                + response.status
            );

        }


        let output = "";


        if (data.stdout) {

            output +=
                data.stdout;

        }


        if (data.stderr) {

            if (output) {

                output +=
                    "\n";

            }

            output +=
                data.stderr;

        }


        if (!output) {

            output =
                "(Program finished with no output.)";

        }


        resultBox.textContent =
            output;


        if (data.success) {

            setStatus(
                "Finished",
                "success"
            );

        }

        else if (
            data.phase === "compile"
        ) {

            setStatus(
                "Compilation Error",
                "error"
            );

        }

        else if (
            data.timeout
        ) {

            setStatus(
                "Timeout",
                "error"
            );

        }

        else {

            setStatus(
                "Runtime Error",
                "error"
            );

        }

    }

    catch (error) {

        resultBox.textContent =
            "CodeLab server error:\n\n"
            + error.message;

        setStatus(
            "Server Error",
            "error"
        );

    }

    finally {

        runButton.disabled =
            false;

    }

}


/* ========================================================
   JAVASCRIPT
   ======================================================== */

function runJavaScriptInBrowser() {

    const code =
        codeBox.value;

    const messages = [];


    const originalLog =
        console.log;

    const originalError =
        console.error;


    console.log = (...args) => {

        messages.push(
            args
                .map(formatValue)
                .join(" ")
        );

    };


    console.error = (...args) => {

        messages.push(
            "ERROR: "
            +
            args
                .map(formatValue)
                .join(" ")
        );

    };


    try {

        const fn =
            new Function(code);

        fn();


        resultBox.textContent =
            messages.length
                ? messages.join("\n")
                : "JavaScript finished with no console output.";


        setStatus(
            "Finished",
            "success"
        );

    }

    catch (error) {

        resultBox.textContent =
            error.stack ||
            String(error);

        setStatus(
            "Runtime Error",
            "error"
        );

    }

    finally {

        console.log =
            originalLog;

        console.error =
            originalError;

    }

}


/* ========================================================
   FORMAT JAVASCRIPT VALUES
   ======================================================== */

function formatValue(value) {

    if (
        typeof value === "object"
    ) {

        try {

            return JSON.stringify(
                value
            );

        }

        catch {

            return String(value);

        }

    }

    return String(value);

}


/* ========================================================
   RUN
   ======================================================== */

async function runCode() {

    const language =
        currentLanguage();


    /* HTML */

    if (
        language === "html"
    ) {

        renderBrowserCode();

        resultBox.textContent =
            "Preview updated in the Browser Preview panel.";

        setStatus(
            "Finished",
            "success"
        );

        return;

    }


    /* CSS */

    if (
        language === "css"
    ) {

        renderBrowserCode();

        resultBox.textContent =
            "Preview updated in the Browser Preview panel.";

        setStatus(
            "Finished",
            "success"
        );

        return;

    }


    /* JavaScript */

    if (
        language === "javascript"
    ) {

        runJavaScriptInBrowser();

        return;

    }


    /* Python */

    if (
        language === "python"
    ) {

        await runServerCode();

        return;

    }


    /* C */

    if (
        language === "c"
    ) {

        await runServerCode();

        return;

    }

}


/* ========================================================
   RUNTIME CHECK
   ======================================================== */

async function checkRuntime() {

    try {

        const response =
            await fetch(
                "/api/runtime"
            );


        if (!response.ok) {

            throw new Error(
                "Runtime endpoint unavailable."
            );

        }


        const data =
            await response.json();


        const python =
            data.python ||
            "Python unavailable";


        const gcc =
            data.gcc_available
                ? "GCC ready"
                : "GCC unavailable";


        runtimeStatus.textContent =
            python
            + " • "
            + gcc;

    }

    catch {

        runtimeStatus.textContent =
            "Server runtime unavailable";

    }

}


/* ========================================================
   EVENTS
   ======================================================== */

languageSelect.addEventListener(
    "change",
    loadExample
);


runButton.addEventListener(
    "click",
    runCode
);


resetButton.addEventListener(
    "click",
    loadExample
);


clearButton.addEventListener(
    "click",
    () => {

        codeBox.value =
            "";

        inputBox.value =
            "";

        resultBox.textContent =
            "";

        setStatus(
            "Ready"
        );


        if (
            currentLanguage() === "html" ||
            currentLanguage() === "css" ||
            currentLanguage() === "javascript"
        ) {

            renderBrowserCode();

        }

    }
);


/* ========================================================
   OPEN PREVIEW
   ======================================================== */

openPreviewButton.addEventListener(
    "click",
    () => {

        const html =
            preview.srcdoc;


        if (!html) {

            return;

        }


        const blob =
            new Blob(
                [html],
                {
                    type: "text/html"
                }
            );


        const url =
            URL.createObjectURL(
                blob
            );


        window.open(
            url,
            "_blank"
        );

    }
);


/* ========================================================
   TAB SUPPORT
   ======================================================== */

codeBox.addEventListener(
    "keydown",
    (event) => {

        if (
            event.key === "Tab"
        ) {

            event.preventDefault();


            const start =
                codeBox.selectionStart;

            const end =
                codeBox.selectionEnd;


            codeBox.value =
                codeBox.value.substring(
                    0,
                    start
                )
                +
                "    "
                +
                codeBox.value.substring(
                    end
                );


            codeBox.selectionStart =
                codeBox.selectionEnd =
                    start + 4;

        }

    }
);


/* ========================================================
   LIVE BROWSER PREVIEW
   ======================================================== */

codeBox.addEventListener(
    "input",
    () => {

        const language =
            currentLanguage();


        if (
            language === "html" ||
            language === "css" ||
            language === "javascript"
        ) {

            renderBrowserCode();

        }

    }
);


/* ========================================================
   START
   ======================================================== */

loadExample();

checkRuntime();
