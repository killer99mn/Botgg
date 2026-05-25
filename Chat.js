let chat = document.getElementById("chat");
let input = document.getElementById("msg");

function add(msg) {
    chat.innerHTML += "<div>" + msg + "</div>";
    chat.scrollTop = chat.scrollHeight;
}

let ws;

function connectWS() {
    try {
        ws = new WebSocket("ws://" + location.hostname + ":5000/ws");

        ws.onmessage = (e) => add(e.data);

        ws.onopen = () => add("Connected via WebSocket");

        ws.onerror = () => fallbackMode();

        ws.onclose = () => fallbackMode();
    } catch {
        fallbackMode();
    }
}

function fallbackMode() {
    add("WebSocket failed, switching to fallback...");
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            fetch("/poll", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({msg: input.value})
            });
            input.value = "";
        }
    });
}

input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && ws && ws.readyState === 1) {
        ws.send(input.value);
        input.value = "";
    }
});

connectWS();
