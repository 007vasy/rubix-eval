/**
 * Server-owned Puppeteer cube. JSON lines on stdin/stdout.
 * State is injected via CDP, never served to the agent HTTP API.
 */
import { createRequire } from "node:module";
import readline from "node:readline";
import fs from "node:fs";

const require = createRequire(import.meta.url);
const puppeteerCandidates = [
  process.env.PUPPETEER_MODULE,
  "/home/ben/.npm/_npx/7d92d9a2d2ccc630/node_modules/puppeteer",
].filter(Boolean);
let puppeteer;
for (const candidate of puppeteerCandidates) {
  try {
    puppeteer = require(candidate);
    break;
  } catch {
    /* try next */
  }
}
if (!puppeteer) {
  puppeteer = require("puppeteer");
}

const origin = process.argv[2] || "http://127.0.0.1:8765";
const chrome = process.env.RUBIX_CHROME || "/usr/bin/google-chrome";

const browser = await puppeteer.launch({
  headless: "new",
  executablePath: fs.existsSync(chrome) ? chrome : undefined,
  pipe: true,
  args: [
    "--no-first-run",
    "--no-default-browser-check",
    "--use-angle=swiftshader",
    "--enable-unsafe-swiftshader",
    "--window-size=1280,800",
  ],
  defaultViewport: { width: 1280, height: 800 },
});

let sharedPage = null;

async function pageFor() {
  if (sharedPage && !sharedPage.isClosed()) return sharedPage;
  const page = await browser.newPage();
  await page.setViewport({ width: 1280, height: 800 });
  await page.goto(`${origin}/renderer.html`, { waitUntil: "domcontentloaded", timeout: 20000 });
  await page.waitForFunction(() => window.__trusted, { timeout: 15000 });
  sharedPage = page;
  return page;
}

async function handle(msg) {
  const { op, id } = msg;
  if (op === "ping") return { ok: true };
  if (op === "close") {
    if (sharedPage) await sharedPage.close().catch(() => {});
    await browser.close();
    return { ok: true, bye: true };
  }
  if (!id) return { ok: false, error: "missing id" };
  const page = await pageFor();
  if (op === "load") {
    await page.evaluate(
      (kind, state) => window.__trusted.load(kind, state),
      msg.kind || "3d",
      msg.state,
    );
    await new Promise((r) => setTimeout(r, 200));
    return { ok: true };
  }
  if (op === "click") {
    const pick = await page.evaluate(
      (x, y, button, dbl) => window.__trusted.pointer(x, y, button, dbl),
      msg.x,
      msg.y,
      msg.button || 0,
      Boolean(msg.dbl),
    );
    await new Promise((r) => setTimeout(r, 650));
    const snap = await page.evaluate(() => window.__trusted.snapshot());
    return { ok: true, pick, ...snap };
  }
  if (op === "orbit") {
    const x0 = msg.x ?? 80;
    const y0 = msg.y ?? 200;
    const x1 = x0 + (msg.dx || 0);
    const y1 = y0 + (msg.dy || 0);
    await page.mouse.move(x0, y0);
    await page.mouse.down();
    const steps = 20;
    for (let i = 1; i <= steps; i += 1) {
      await page.mouse.move(x0 + ((x1 - x0) * i) / steps, y0 + ((y1 - y0) * i) / steps);
    }
    await page.mouse.up();
    await new Promise((r) => setTimeout(r, 400));
    return { ok: true };
  }
  if (op === "shot") {
    const buf = await page.screenshot({ type: "png" });
    return { ok: true, png: buf.toString("base64") };
  }
  if (op === "drop") {
    return { ok: true };
  }
  return { ok: false, error: "unknown op " + op };
}

const rl = readline.createInterface({ input: process.stdin, crlfDelay: Infinity });
for await (const line of rl) {
  if (!line.trim()) continue;
  let msg;
  try {
    msg = JSON.parse(line);
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(e) }) + "\n");
    continue;
  }
  try {
    const result = await handle(msg);
    process.stdout.write(JSON.stringify(result) + "\n");
    if (result.bye) process.exit(0);
  } catch (e) {
    process.stdout.write(JSON.stringify({ ok: false, error: String(e.stack || e) }) + "\n");
  }
}
