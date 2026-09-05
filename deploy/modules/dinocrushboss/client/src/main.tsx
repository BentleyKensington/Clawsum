import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

function reportError(message: string, fingerprint: string, stack?: string) {
  fetch("/api/ingest/error", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, fingerprint, stack, platform: "web" }),
  }).catch(() => {});
}

window.addEventListener("error", (event) => {
  const fingerprint = `${event.filename || "window"}:${event.lineno || 0}:${event.message}`;
  reportError(event.message || "error", fingerprint, event.error?.stack);
});

window.addEventListener("unhandledrejection", (event) => {
  const message = event.reason instanceof Error ? event.reason.message : String(event.reason || "rejection");
  const stack = event.reason instanceof Error ? event.reason.stack : undefined;
  reportError(message, `unhandled:${message}`, stack);
});

createRoot(document.getElementById("root")!).render(<App />);
