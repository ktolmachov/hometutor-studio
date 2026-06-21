import { describe, it, expect, vi, afterEach } from "vitest";
import { parseDeepseekCliCmd, needsWindowsShell } from "../../scripts/deepseek_tui_agent_trigger.js";

// ── parseDeepseekCliCmd ──────────────────────────────────────────────────────

describe("parseDeepseekCliCmd", () => {
  it("empty string → default deepseek", () => {
    expect(parseDeepseekCliCmd("")).toEqual({ bin: "deepseek", prefixArgs: [] });
    expect(parseDeepseekCliCmd("   ")).toEqual({ bin: "deepseek", prefixArgs: [] });
  });

  it("bare binary name", () => {
    expect(parseDeepseekCliCmd("deepseek")).toEqual({ bin: "deepseek", prefixArgs: [] });
  });

  it("explicit .cmd wrapper", () => {
    expect(parseDeepseekCliCmd("deepseek.cmd")).toEqual({ bin: "deepseek.cmd", prefixArgs: [] });
  });

  it("python + script (no spaces in paths)", () => {
    expect(parseDeepseekCliCmd("python.exe C:\\scripts\\fake.py")).toEqual({
      bin: "python.exe",
      prefixArgs: ["C:\\scripts\\fake.py"],
    });
  });

  it("python3 + script on unix", () => {
    expect(parseDeepseekCliCmd("/usr/bin/python3 /home/user/fake.py")).toEqual({
      bin: "/usr/bin/python3",
      prefixArgs: ["/home/user/fake.py"],
    });
  });

  it("quoted python path with spaces + script", () => {
    const cmd = '"C:\\Program Files\\Python311\\python.exe" C:\\scripts\\fake.py';
    expect(parseDeepseekCliCmd(cmd)).toEqual({
      bin: "C:\\Program Files\\Python311\\python.exe",
      prefixArgs: ["C:\\scripts\\fake.py"],
    });
  });

  it("quoted python path + quoted script path (both with spaces)", () => {
    const cmd = '"C:\\path with spaces\\python.exe" "C:\\tmp\\my script.py"';
    expect(parseDeepseekCliCmd(cmd)).toEqual({
      bin: "C:\\path with spaces\\python.exe",
      prefixArgs: ["C:\\tmp\\my script.py"],
    });
  });

  it("multiple prefix args (e.g. python -m module script)", () => {
    expect(parseDeepseekCliCmd("python.exe -m my_module script.py")).toEqual({
      bin: "python.exe",
      prefixArgs: ["-m", "my_module", "script.py"],
    });
  });

  it("unclosed quote: consumes rest of string as bin", () => {
    // Malformed input: graceful degradation — rest treated as one token
    const result = parseDeepseekCliCmd('"unclosed');
    expect(result.bin).toBe("unclosed");
    expect(result.prefixArgs).toEqual([]);
  });

  it("leading/trailing whitespace is trimmed", () => {
    expect(parseDeepseekCliCmd("  python.exe script.py  ")).toEqual({
      bin: "python.exe",
      prefixArgs: ["script.py"],
    });
  });
});

// ── needsWindowsShell ────────────────────────────────────────────────────────

describe("needsWindowsShell", () => {
  const originalPlatform = process.platform;

  function setPlatform(p: string) {
    Object.defineProperty(process, "platform", { value: p, configurable: true });
  }

  afterEach(() => {
    Object.defineProperty(process, "platform", { value: originalPlatform, configurable: true });
  });

  it("returns false on non-Windows regardless of bin name", () => {
    setPlatform("linux");
    expect(needsWindowsShell("deepseek")).toBe(false);
    expect(needsWindowsShell("deepseek.cmd")).toBe(false);
    expect(needsWindowsShell("python.exe")).toBe(false);
  });

  it("returns true for bare command name on Windows (npm .cmd wrapper)", () => {
    setPlatform("win32");
    expect(needsWindowsShell("deepseek")).toBe(true);
    expect(needsWindowsShell("node")).toBe(true);
  });

  it("returns true for explicit .cmd on Windows", () => {
    setPlatform("win32");
    expect(needsWindowsShell("deepseek.cmd")).toBe(true);
    expect(needsWindowsShell("DEEPSEEK.CMD")).toBe(true);
  });

  it("returns true for explicit .bat on Windows", () => {
    setPlatform("win32");
    expect(needsWindowsShell("run.bat")).toBe(true);
  });

  it("returns false for .exe on Windows (direct spawn)", () => {
    setPlatform("win32");
    expect(needsWindowsShell("python.exe")).toBe(false);
    expect(needsWindowsShell("C:\\Python311\\python.exe")).toBe(false);
  });

  it("returns false for .py script on Windows (direct spawn via python)", () => {
    setPlatform("win32");
    expect(needsWindowsShell("C:\\scripts\\fake.py")).toBe(false);
  });

  it("returns false for absolute path without extension on Windows (unambiguous)", () => {
    setPlatform("win32");
    // Absolute paths are unambiguous — spawn directly
    expect(needsWindowsShell("C:\\bin\\deepseek")).toBe(false);
    expect(needsWindowsShell("/usr/local/bin/deepseek")).toBe(false);
  });
});
