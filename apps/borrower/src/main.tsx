import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import { appState } from "./lib/state";
import { ToastProvider } from "./ui";
import "./styles.css";

// basename strips the /app/ prefix so routes read like the Flutter app (/score, not /app/score)
const basename = import.meta.env.BASE_URL.replace(/\/$/, "");

appState.restore().finally(() => {
  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <BrowserRouter basename={basename}>
        <ToastProvider>
          <App />
        </ToastProvider>
      </BrowserRouter>
    </React.StrictMode>,
  );
});
