/**
 * FastAPI + Streamlit for Playwright PR smoke (offline; no live LLM).
 * Used by playwright.config.ts webServer on Windows/Linux/macOS CI.
 */
import { spawn, spawnSync } from 'node:child_process';
import fs from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

/** Prefer repo .venv so Streamlit/uvicorn match `pip install -r requirements.txt` (CI uses bare `python`). */
function resolvePython(projectRoot) {
  if (process.env.PYTHON) {
    return process.env.PYTHON;
  }
  const win = process.platform === 'win32';
  const candidates = win
    ? [path.join(projectRoot, '.venv', 'Scripts', 'python.exe')]
    : [
        path.join(projectRoot, '.venv', 'bin', 'python3'),
        path.join(projectRoot, '.venv', 'bin', 'python'),
      ];
  for (const c of candidates) {
    if (fs.existsSync(c)) {
      return c;
    }
  }
  return win ? 'python' : 'python3';
}

const host = process.env.E2E_API_HOST ?? '127.0.0.1';
const apiPort = process.env.E2E_API_PORT ?? '18000';
const stPort = process.env.E2E_STREAMLIT_PORT ?? '18501';
const requestedWorkers = Math.max(
  1,
  Number.parseInt(process.env.PLAYWRIGHT_WORKERS ?? process.env.DEMO_WORKERS ?? '1', 10) || 1,
);
const py = resolvePython(root);

/** Fresh SQLite so PR smoke is isolated from developer data/user_state.db. */
const e2eDir = path.join(root, '.e2e');
const e2eUserStateDb = path.join(e2eDir, 'state-main.db');
const workerStateDbs = Array.from({ length: requestedWorkers }, (_, idx) =>
  path.join(e2eDir, `state-${idx}.db`),
);
fs.mkdirSync(e2eDir, { recursive: true });
try {
  fs.unlinkSync(e2eUserStateDb);
} catch (err) {
  if (err && err.code !== 'ENOENT') throw err;
}
for (const dbPath of workerStateDbs) {
  try {
    fs.unlinkSync(dbPath);
  } catch (err) {
    if (err && err.code !== 'ENOENT') throw err;
  }
}

const env = { ...process.env, PYTHONUNBUFFERED: '1' };
if (env.OPENAI_API_KEY === undefined) env.OPENAI_API_KEY = '';
/** Playwright smoke: deterministic flashcard generation without OpenAI (see flashcard_service). */
env.HOME_RAG_E2E_OFFLINE = '1';
/** Disable log rotation in e2e to avoid Windows file-lock rollover errors. */
env.HOME_RAG_E2E_NO_LOG_ROTATE = '1';
// Force isolated DB even if shell/user env defines USER_STATE_DB.
env.USER_STATE_DB = e2eUserStateDb;
for (let idx = 0; idx < workerStateDbs.length; idx += 1) {
  env[`USER_STATE_DB_${idx}`] = workerStateDbs[idx];
}
env.UI_API_BASE_URL = `http://${host}:${apiPort}`;
const corsOrigins = new Set(
  (env.CORS_ORIGINS ?? '')
    .split(',')
    .map((x) => x.trim())
    .filter(Boolean),
);
corsOrigins.add(`http://${host}:${stPort}`);
corsOrigins.add(`http://localhost:${stPort}`);
env.CORS_ORIGINS = Array.from(corsOrigins).join(',');

/**
 * Deterministic e2e profile:
 * pre-seed onboarding flag so sidebar/home controls are available without
 * depending on Streamlit button timing during the first rerun.
 */
const seedTargets = [e2eUserStateDb, ...workerStateDbs];
const seed = spawnSync(
  py,
  [
    '-c',
    [
      'import sqlite3, pathlib',
      `targets = [${seedTargets.map((x) => `r"""${x}"""`).join(', ')}]`,
      'for item in targets:',
      '    db = pathlib.Path(item)',
      '    db.parent.mkdir(parents=True, exist_ok=True)',
      '    conn = sqlite3.connect(str(db))',
      '    conn.execute("CREATE TABLE IF NOT EXISTS app_kv (key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TEXT NOT NULL)")',
      '    conn.execute("INSERT INTO app_kv(key, value, updated_at) VALUES (?, ?, datetime(\'now\')) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at", ("onboarding_v1_done", "1"))',
      '    conn.commit()',
      '    conn.close()',
    ].join('\n'),
  ],
  {
    cwd: root,
    env,
    stdio: 'inherit',
  },
);
if (seed.status !== 0) {
  process.exit(seed.status ?? 1);
}

const uv = spawn(py, ['-m', 'uvicorn', 'app.api:app', '--host', host, '--port', String(apiPort)], {
  cwd: root,
  env,
  stdio: 'inherit',
});

const apiHealthUrl = `http://${host}:${apiPort}/health`;
const streamlitHealthUrl = `http://${host}:${stPort}/_stcore/health`;

/** Ждём FastAPI до старта Streamlit — иначе Playwright (poll только :8501) начинает тесты при «ещё не поднятом» :8000. */
async function waitForHttpOk(label, url, attempts = 60) {
  let lastStatus = '';
  let lastBody = '';
  let lastError = '';
  for (let i = 0; i < attempts; i += 1) {
    try {
      const r = await fetch(url, { signal: AbortSignal.timeout(3000) });
      lastStatus = `${r.status} ${r.statusText}`;
      lastBody = (await r.text()).slice(0, 1000);
      if (r.ok) return;
    } catch (err) {
      lastError = err instanceof Error ? err.message : String(err);
    }
    await new Promise((r) => setTimeout(r, 500));
  }
  console.error(`e2e stack: ${label} not ready (${url})`);
  if (lastStatus) console.error(`e2e stack: last HTTP status: ${lastStatus}`);
  if (lastBody) console.error(`e2e stack: last HTTP body: ${lastBody}`);
  if (lastError) console.error(`e2e stack: last error: ${lastError}`);
  try {
    uv.kill('SIGTERM');
  } catch {
    /* ignore */
  }
  process.exit(1);
}

await waitForHttpOk('FastAPI', apiHealthUrl);

/**
 * Streamlit + Tornado пишут в stderr «Task exception was never retrieved» /
 * WebSocketClosedError, когда клиент (Playwright) резко рвёт WS — это не баг приложения.
 * Фильтруем только блоки, где явно фигурирует disconnect WebSocket.
 */
function pipeStreamlitStderrFiltered(child) {
  if (!child.stderr) return;
  let lineBuf = '';
  /** @type {string[]} */
  let hold = [];
  let holding = false;

  const isAppJsonLog = (s) => /^\{"timestamp":/.test(s);

  const flushHold = (discard) => {
    if (!holding) return;
    if (!discard) {
      for (const ln of hold) process.stderr.write(ln);
    }
    hold = [];
    holding = false;
  };

  child.stderr.on('data', (chunk) => {
    lineBuf += chunk.toString('utf8');
    let idx;
    while ((idx = lineBuf.indexOf('\n')) >= 0) {
      const line = lineBuf.slice(0, idx + 1);
      lineBuf = lineBuf.slice(idx + 1);
      const text = line.replace(/\r\n/g, '\n').replace(/\r$/, '');

      if (holding) {
        hold.push(line);
        if (isAppJsonLog(text)) {
          flushHold(true);
          process.stderr.write(line);
          continue;
        }
        const joined = hold.join('');
        if (hold.length > 120) {
          flushHold(false);
          continue;
        }
        if (hold.length >= 4 && !/(WebSocketClosedError|StreamClosedError|websocket\.py|iostream\.py)/i.test(joined)) {
          flushHold(false);
          continue;
        }
        continue;
      }

      if (text.includes('Task exception was never retrieved')) {
        holding = true;
        hold = [line];
        continue;
      }

      process.stderr.write(line);
    }
  });

  child.stderr.on('end', () => {
    if (lineBuf) {
      if (holding) hold.push(lineBuf);
      else process.stderr.write(lineBuf);
      lineBuf = '';
    }
    if (holding) {
      const joined = hold.join('');
      const discard =
        /(WebSocketClosedError|StreamClosedError|websocket\.py|iostream\.py)/i.test(joined);
      flushHold(!discard);
    }
  });
}

const st = spawn(
  py,
  [
    '-m',
    'streamlit',
    'run',
    'app/ui/main.py',
    '--server.address',
    host,
    '--server.port',
    String(stPort),
    '--server.headless',
    'true',
    '--browser.gatherUsageStats',
    'false',
  ],
  {
    cwd: root,
    env,
    stdio: ['inherit', 'inherit', 'pipe'],
  },
);
pipeStreamlitStderrFiltered(st);

function shutdown(sig) {
  try {
    st.kill(sig);
  } catch {
    /* ignore */
  }
  try {
    uv.kill(sig);
  } catch {
    /* ignore */
  }
}

await waitForHttpOk('Streamlit', streamlitHealthUrl);

process.on('SIGINT', () => {
  shutdown('SIGTERM');
  process.exit(0);
});
process.on('SIGTERM', () => {
  shutdown('SIGTERM');
  process.exit(0);
});

uv.on('exit', (code) => {
  if (code && code !== 0) process.exit(code);
});
st.on('exit', (code) => {
  if (code && code !== 0) process.exit(code);
});
