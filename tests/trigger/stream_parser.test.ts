import { describe, it, expect } from "vitest";
import {
  parseStreamJsonLine,
  StreamJsonAccumulator,
} from "../../scripts/_trigger_shared.js";

describe("parseStreamJsonLine", () => {
  it("returns null for empty lines", () => {
    expect(parseStreamJsonLine("")).toBeNull();
    expect(parseStreamJsonLine("  ")).toBeNull();
  });

  it("returns null for non-JSON", () => {
    expect(parseStreamJsonLine("not json")).toBeNull();
  });

  it("returns null for JSON without type field", () => {
    expect(parseStreamJsonLine('{"foo": "bar"}')).toBeNull();
  });

  it("parses valid stream event", () => {
    const event = parseStreamJsonLine('{"type": "metadata", "model": "deepseek-v4-flash"}');
    expect(event).toEqual({ type: "metadata", model: "deepseek-v4-flash" });
  });
});

describe("StreamJsonAccumulator", () => {
  it("accumulates happy path stream into correct result", () => {
    const acc = new StreamJsonAccumulator();
    acc.feed('{"type": "tool_use", "tool": "read_file", "path": "README.md"}');
    acc.feed('{"type": "tool_result", "status": "ok", "content": "..."}');
    acc.feed('{"type": "tool_use", "tool": "write_file", "path": "out.md"}');
    acc.feed('{"type": "tool_result", "status": "ok"}');
    acc.feed('{"type": "content", "content": "Done."}');
    acc.feed('{"type": "metadata", "status": "completed", "model": "deepseek-v4-flash", "input_tokens": 61000, "output_tokens": 275}');
    acc.feed('{"type": "done"}');

    const r = acc.result();
    expect(r.metadata).toBeTruthy();
    expect(r.metadata!.status).toBe("completed");
    expect(r.metadata!.input_tokens).toBe(61000);
    expect(r.toolUseCount).toBe(2);
    expect(r.toolSuccessCount).toBe(2);
    expect(r.toolErrorCount).toBe(0);
    expect(r.contentPreview).toBe("Done.");
    expect(r.doneReceived).toBe(true);
    expect(r.sessionError).toBeNull();
  });

  it("marks session error on type:error event (hard fail)", () => {
    const acc = new StreamJsonAccumulator();
    acc.feed('{"type": "error", "message": "session crashed"}');

    const r = acc.result();
    expect(r.sessionError).toBe("session crashed");
  });

  it("counts tool errors without marking session error (soft fail)", () => {
    const acc = new StreamJsonAccumulator();
    acc.feed('{"type": "tool_use", "tool": "read_file"}');
    acc.feed('{"type": "tool_result", "is_error": true, "error": "file not found"}');
    acc.feed('{"type": "tool_use", "tool": "read_file"}');
    acc.feed('{"type": "tool_result", "status": "ok"}');
    acc.feed('{"type": "metadata", "status": "completed"}');
    acc.feed('{"type": "done"}');

    const r = acc.result();
    expect(r.sessionError).toBeNull();
    expect(r.toolErrorCount).toBe(1);
    expect(r.toolSuccessCount).toBe(1);
    expect(r.toolUseCount).toBe(2);
    expect(r.doneReceived).toBe(true);
  });
});
