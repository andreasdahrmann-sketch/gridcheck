import assert from "node:assert/strict";
import test from "node:test";

async function importNextConfig(caseName) {
  return import(new URL(`../../next.config.mjs?case=${caseName}-${Date.now()}`, import.meta.url).href);
}

function withBackendEnv(env, fn) {
  const previous = {
    BACKEND_URL: process.env.BACKEND_URL,
    VERCEL: process.env.VERCEL,
  };
  if ("BACKEND_URL" in env) {
    if (env.BACKEND_URL === undefined) delete process.env.BACKEND_URL;
    else process.env.BACKEND_URL = env.BACKEND_URL;
  }
  if ("VERCEL" in env) {
    if (env.VERCEL === undefined) delete process.env.VERCEL;
    else process.env.VERCEL = env.VERCEL;
  }
  return Promise.resolve()
    .then(fn)
    .finally(() => {
      if (previous.BACKEND_URL === undefined) delete process.env.BACKEND_URL;
      else process.env.BACKEND_URL = previous.BACKEND_URL;
      if (previous.VERCEL === undefined) delete process.env.VERCEL;
      else process.env.VERCEL = previous.VERCEL;
    });
}

test("next config fails closed on Vercel when BACKEND_URL is missing", async () => {
  await withBackendEnv({ VERCEL: "1", BACKEND_URL: undefined }, async () => {
    await assert.rejects(
      () => importNextConfig("vercel-missing-backend-url"),
      /BACKEND_URL fehlt auf Vercel/,
    );
  });
});

test("next config uses the explicit Vercel BACKEND_URL for rewrites", async () => {
  await withBackendEnv(
    { VERCEL: "1", BACKEND_URL: "https://api.example.test/" },
    async () => {
      const { default: config } = await importNextConfig("vercel-explicit-backend-url");
      const rewrites = await config.rewrites();
      assert.deepEqual(rewrites, [
        {
          source: "/api/backend/:path*",
          destination: "https://api.example.test/:path*",
        },
      ]);
    },
  );
});
