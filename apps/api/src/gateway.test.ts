import { describe, it, expect, beforeEach } from "vitest";
import * as gateway from "./gateway.js";
import * as sessionStore from "./sessionStore.js";

describe("Gateway", () => {
  it("getOrCreateSession returns new session when null", () => {
    const sid = gateway.getOrCreateSession(null);
    expect(sid).toBeDefined();
    expect(sid.length).toBe(12);
  });

  it("toStandardMessage normalizes content and has session_id", () => {
    const msg = gateway.toStandardMessage("hello", null);
    expect(msg.content).toBe("hello");
    expect(msg.session_id).toBeDefined();
    expect(msg.user_id).toBe("default");
    expect(msg.message_id).toBeDefined();
  });

  it("appendUserTurn and getHistoryForControl", () => {
    const sid = gateway.getOrCreateSession(null);
    gateway.appendUserTurn(sid, "hi");
    gateway.appendAssistantTurn(sid, "bye", []);
    const history = gateway.getHistoryForControl(sid);
    expect(history.length).toBe(2);
    expect(history[0].role).toBe("user");
    expect(history[0].content).toBe("hi");
    expect(history[1].content).toBe("bye");
  });
});
