import assert from "node:assert/strict";
import test from "node:test";

function snapshotEnv() {
  return {
    ANALYZE: process.env.ANALYZE,
    BACKEND_URL: process.env.BACKEND_URL,
    VERCEL: process.env.VERCEL,
  };
}

function restoreEnv(snapshot) {
  for (const [key, value] of Object.entries(snapshot)) {
    if (value === undefined) {
      delete process.env[key];
    } else {
      process.env[key] = value;
    }
  }
}

test("next config fails closed on Vercel when BACKEND_URL is missing", async () => {
  const env = snapshotEnv();
  try {
    process.env.VERCEL = "1";
    delete process.env.BACKEND_URL;
    delete process.env.ANALYZE;

    await assert.rejects(
      import(`./next.config.mjs?missing-backend=${Date.now()}`),
      /BACKEND_URL fehlt auf Vercel/,
    );
  } finally {
    restoreEnv(env);
  }
});

test("next config accepts an explicit Vercel BACKEND_URL", async () => {
  const env = snapshotEnv();
  try {
    process.env.VERCEL = "1";
    process.env.BACKEND_URL = "https://api.gridcheck.example";
    delete process.env.ANALYZE;

    const mod = await import(`./next.config.mjs?explicit-backend=${Date.now()}`);
    assert.equal(typeof mod.default.rewrites, "function");
  } finally {
    restoreEnv(env);
  }
});
