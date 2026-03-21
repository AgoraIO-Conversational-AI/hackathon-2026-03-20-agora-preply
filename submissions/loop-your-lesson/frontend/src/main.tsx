import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

// StrictMode disabled: it double-mounts effects, creating duplicate ConvoAI agents
createRoot(document.getElementById("root")!).render(<App />);
