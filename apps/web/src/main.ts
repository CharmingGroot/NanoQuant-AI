import "./dashboard-tab.js";
import "./chat-tab.js";
import "./backtest-tab.js";
import "./monitor-tab.js";
import "./kg-tab.js";
import "./settings-tab.js";
import { NanoQuantApp } from "./nanoquant-app.js";

const app = document.getElementById("app");
if (app) {
  app.appendChild(new NanoQuantApp());
}
