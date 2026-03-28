const { test, expect } = require("@playwright/test");

const DEMO_TEACHER = {
  username: "demo_teacher",
  password: "DemoPass123!",
};

function formatDateTimeLocal(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join("-") + `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

test("teacher can log in and create a draft exam", async ({ page }) => {
  const uniqueTitle = `Playwright Demo ${Date.now()}`;
  const startAt = new Date(Date.now() + 24 * 60 * 60 * 1000);
  startAt.setSeconds(0, 0);
  const endAt = new Date(startAt.getTime() + 60 * 60 * 1000);

  await page.goto("/connexion/");

  await page.locator('input[name="username"]').fill(DEMO_TEACHER.username);
  await page.locator('input[name="password"]').fill(DEMO_TEACHER.password);
  await page.getByRole("button", { name: "Se connecter" }).click();

  await expect(page).toHaveURL(/\/enseignant\/examens\/$/);
  await expect(page.getByRole("heading", { name: "Mes examens" })).toBeVisible();

  await page.getByRole("link", { name: "Nouvel examen" }).click();

  await expect(page).toHaveURL(/\/enseignant\/examens\/nouveau\/$/);
  await page.locator('input[name="titre"]').fill(uniqueTitle);
  await page.locator('textarea[name="description"]').fill(
    "Examen de demonstration automatise avec Playwright."
  );
  await page.locator('input[name="heure_debut"]').fill(formatDateTimeLocal(startAt));
  await page.locator('input[name="heure_fin"]').fill(formatDateTimeLocal(endAt));
  await page.locator('select[name="statut"]').selectOption("BROUILLON");

  await page.getByRole("button", { name: "Creer" }).click();

  await expect(page).toHaveURL(/\/enseignant\/examens\/\d+\/$/);
  await expect(page.getByText("Examen cree.")).toBeVisible();
  await expect(page.locator('input[name="titre"]')).toHaveValue(uniqueTitle);

  await page.getByRole("link", { name: "Retour" }).click();

  await expect(page).toHaveURL(/\/enseignant\/examens\/$/);
  await expect(page.getByRole("cell", { name: uniqueTitle })).toBeVisible();
});
