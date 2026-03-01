/**
 * API 서버만 실행 (빌드된 dist 사용). 웹은 별도 터미널에서: pnpm --filter web run dev
 */
import { spawn } from "child_process";
import { fileURLToPath } from "url";
import { dirname, join } from "path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const apiDir = join(__dirname, "..", "apps", "api");

const child = spawn("node", ["dist/index.js"], {
  cwd: apiDir,
  stdio: "inherit",
  shell: true,
});

child.on("exit", (code) => process.exit(code ?? 0));
