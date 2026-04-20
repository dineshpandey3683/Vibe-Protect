import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

// Register the service worker in production only. Under `yarn start`
// we never install the SW because its aggressive caching would fight
// the webpack dev-server's HMR. The SW itself handles versioning +
// stale-cache eviction on every deploy.
if ("serviceWorker" in navigator && process.env.NODE_ENV === "production") {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/service-worker.js")
      .catch((err) => {
        // eslint-disable-next-line no-console
        console.warn("[vibe-protect] SW registration failed:", err);
      });
  });
}
