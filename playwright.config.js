const { defineConfig } = require("@playwright/test");

const isWindows = process.platform === "win32";
const webServerCommand = isWindows
  ? "powershell -ExecutionPolicy Bypass -File scripts/start_playwright_demo.ps1"
  : ".venv/bin/python manage.py migrate --noinput && .venv/bin/python scripts/seed_playwright_demo.py && .venv/bin/python manage.py runserver 127.0.0.1:8000 --noreload";

module.exports = defineConfig({
  testDir: "./playwright/tests",
  fullyParallel: false,
  workers: 1,
  timeout: 30_000,
  expect: {
    timeout: 10_000,
  },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: "http://127.0.0.1:8000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    viewport: { width: 1440, height: 900 },
    launchOptions: {
  slowMo: Number(process.env.PLAYWRIGHT_SLOW_MO || 0),
},
  },
  projects: [
    {
      name: "chromium",
      use: {
        browserName: "chromium",
      },
    },
  ],
  webServer: {
    command: webServerCommand,
    url: "http://127.0.0.1:8000/connexion/",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
