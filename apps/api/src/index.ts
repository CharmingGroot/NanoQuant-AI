import "dotenv/config";
import express from "express";
import { initDb } from "./db.js";
import * as kg from "./kg.js";
import agentRoutes from "./routes.js";

try {
  initDb();
  kg.initFromDb();
} catch (e) {
  console.warn("SQLite init skipped (KG will be in-memory only):", e instanceof Error ? e.message : e);
}

const app = express();
app.use(express.json());

app.use("/agent", agentRoutes);

app.get("/health", (_req, res) => {
  res.json({ status: "ok", service: "nanoquant-api" });
});

const port = Number(process.env.PORT) || 5051;
app.listen(port, () => {
  console.log(`NanoQuant API: http://127.0.0.1:${port}`);
  console.log(`  /agent/chat  POST - chat`);
  console.log(`  /agent/approve POST - HITL approve`);
  console.log(`  /agent/skills GET - list skills`);
  console.log(`  /agent/kg/recent GET - KG decisions`);
});
