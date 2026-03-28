const { test, expect } = require("@playwright/test");

const DEMO_STUDENT = {
  username: "demo_student",
  password: "DemoPass123!",
};

const ACTIVE_EXAM_TITLE = "Playwright Student Active Exam";
const UPCOMING_EXAM_TITLE = "Playwright Student Upcoming Exam";
const RESULT_EXAM_TITLE = "Playwright Student Corrected Exam";

test("student can log in, view exams, and consult results", async ({ page }) => {
  await page.goto("/connexion/");

  await page.locator('input[name="username"]').fill(DEMO_STUDENT.username);
  await page.locator('input[name="password"]').fill(DEMO_STUDENT.password);
  await page.getByRole("button", { name: "Se connecter" }).click();

  await expect(page).toHaveURL(/\/etudiant\/$/);
  await expect(page.getByText("Espace Etudiant - Tableau de bord")).toBeVisible();
  await expect(page.getByText(ACTIVE_EXAM_TITLE)).toBeVisible();
  await expect(page.getByText(UPCOMING_EXAM_TITLE)).toBeVisible();
  await expect(page.getByRole("heading", { name: "Examens en cours" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Mes resultats" })).toBeVisible();

  await page.getByRole("link", { name: "Mes examens" }).click();

  await expect(page).toHaveURL(/\/etudiant\/examens\/$/);
  await expect(page.getByRole("heading", { name: "Mes examens" })).toBeVisible();
  await expect(page.getByRole("cell", { name: ACTIVE_EXAM_TITLE })).toBeVisible();

  await page.getByRole("link", { name: "Ouvrir" }).first().click();

  await expect(page).toHaveURL(/\/etudiant\/examens\/\d+\/$/);
  await expect(page.getByRole("heading", { name: ACTIVE_EXAM_TITLE })).toBeVisible();
  await expect(
    page.getByText("Examen en cours pour la demonstration Playwright etudiant.")
  ).toBeVisible();
  await expect(page.locator('textarea[name="code_source"]')).toBeVisible();

  await page.getByRole("link", { name: "Mes resultats" }).click();

  await expect(page).toHaveURL(/\/etudiant\/resultats\/$/);
  await expect(page.getByRole("heading", { name: "Mes resultats" })).toBeVisible();
  const resultRow = page.getByRole("row", { name: new RegExp(RESULT_EXAM_TITLE) });
  await expect(resultRow).toBeVisible();
  await expect(resultRow).toContainText("16,50");
  await expect(resultRow).toContainText("Resultat de demonstration Playwright.");
});
