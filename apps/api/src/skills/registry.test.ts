import { describe, it, expect, beforeEach } from "vitest";
import * as registry from "./registry.js";

describe("SkillRegistry", () => {
  beforeEach(() => {
    registry.register("add", "Add two numbers", { a: "number", b: "number" }, (args) => {
      return (args.a as number) + (args.b as number);
    });
  });

  it("listSkills returns meta", () => {
    const list = registry.listSkills();
    expect(list.some((s) => s.name === "add")).toBe(true);
    expect(list.find((s) => s.name === "add")?.description).toBe("Add two numbers");
  });

  it("run executes and returns result", async () => {
    const result = await registry.run("add", { a: 1, b: 2 });
    expect(result).toBe(3);
  });

  it("run unknown skill throws", async () => {
    await expect(registry.run("nonexistent", {})).rejects.toThrow("Unknown skill");
  });
});
