/**
 * API 실행 검증: /health, /agent/skills 호출
 * 사용: node scripts/verify-api.js [baseUrl]
 */
const base = process.argv[2] || "http://127.0.0.1:5051";

async function get(url) {
  const res = await fetch(url);
  const text = await res.text();
  if (!res.ok) throw new Error(`${res.status} ${text}`);
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function main() {
  console.log("Verifying API at", base);
  try {
    const health = await get(`${base}/health`);
    console.log("  GET /health:", health);
    const skills = await get(`${base}/agent/skills`);
    console.log("  GET /agent/skills: skills count =", skills.skills?.length ?? 0);
    const sessions = await get(`${base}/agent/sessions`);
    console.log("  GET /agent/sessions: sessions count =", sessions.sessions?.length ?? 0);
    console.log("OK");
  } catch (e) {
    console.error("FAIL:", e.message);
    process.exit(1);
  }
}

main();
