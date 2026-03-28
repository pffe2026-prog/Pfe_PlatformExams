const fs = require("fs");
const path = require("path");
const { test, expect } = require("@playwright/test");

const DEMO_TEACHER = {
  username: "demo_teacher",
  password: "DemoPass123!",
};

const DEMO_STUDENT = {
  username: "demo_student",
  password: "DemoPass123!",
};

const DEMO_GROUP_LABEL = "PLAYWRIGHT-GI - 2025-2026";
const DEMO_PDF_PATH = path.resolve(__dirname, "..", "fixtures", "demo_exam.pdf");
const DEMO_ENV_PATH = path.resolve(__dirname, "..", "..", ".env");

function readWebhookToken() {
  const envContent = fs.readFileSync(DEMO_ENV_PATH, "utf8");
  const match = envContent.match(/^API_WEBHOOK_TOKEN=(.+)$/m);
  return match ? match[1].trim() : "change_me";
}

test.setTimeout(120_000);

function formatDateTimeLocal(date) {
  const pad = (value) => String(value).padStart(2, "0");
  return [
    date.getFullYear(),
    pad(date.getMonth() + 1),
    pad(date.getDate()),
  ].join("-") + `T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

async function pause(page, ms = 1500) {
  await page.waitForTimeout(ms);
}

test("teacher creates an exam, student submits, then checks the result", async ({
  page,
  request,
}) => {
  const examTitle = `Soutenance Demo ${Date.now()}`;
  const startAt = new Date(Date.now() - 2 * 60 * 60 * 1000);
  startAt.setSeconds(0, 0);
  const endAt = new Date(Date.now() + 2 * 60 * 60 * 1000);
  endAt.setSeconds(0, 0);

  await page.goto("/connexion/");
  await page.locator('input[name="username"]').fill(DEMO_TEACHER.username);
  await page.locator('input[name="password"]').fill(DEMO_TEACHER.password);
  await page.getByRole("button", { name: "Se connecter" }).click();

  await expect(page).toHaveURL(/\/enseignant\/examens\/$/);
  await expect(page.getByRole("heading", { name: "Mes examens" })).toBeVisible();
  await pause(page);

  await page.getByRole("link", { name: "Nouvel examen" }).click();
  await expect(page).toHaveURL(/\/enseignant\/examens\/nouveau\/$/);

  await page.locator('input[name="titre"]').fill(examTitle);
  await page.locator('textarea[name="description"]').fill(
    "Examen de demonstration complet pour la soutenance."
  );
  await page.locator('input[name="pdf_examen"]').setInputFiles(DEMO_PDF_PATH);
  await page.locator('input[name="heure_debut"]').fill(formatDateTimeLocal(startAt));
  await page.locator('input[name="heure_fin"]').fill(formatDateTimeLocal(endAt));
  await page.locator('select[name="statut"]').selectOption("PUBLIE");
  await page.getByText(DEMO_GROUP_LABEL).click();
  await pause(page);

  await page.getByRole("button", { name: "Creer" }).click();

  await expect(page).toHaveURL(/\/enseignant\/examens\/\d+\/$/);
  await expect(page.getByText("Examen cree.")).toBeVisible();
  await expect(page.locator('input[name="titre"]')).toHaveValue(examTitle);
  const examId = Number(page.url().match(/\/(\d+)\/$/)[1]);
  await pause(page, 2000);

  await page.getByRole("button", { name: "Deconnexion" }).first().click();
  await expect(page).toHaveURL(/\/connexion\/$/);
  await pause(page);

  await page.locator('input[name="username"]').fill(DEMO_STUDENT.username);
  await page.locator('input[name="password"]').fill(DEMO_STUDENT.password);
  await page.getByRole("button", { name: "Se connecter" }).click();

  await expect(page).toHaveURL(/\/etudiant\/$/);
  await expect(page.getByText("Espace Etudiant - Tableau de bord")).toBeVisible();
  await pause(page);

  await page.getByRole("link", { name: "Mes examens" }).click();
  await expect(page).toHaveURL(/\/etudiant\/examens\/$/);
  await expect(page.getByRole("cell", { name: examTitle })).toBeVisible();
  await pause(page);

  await page
    .getByRole("row", { name: new RegExp(examTitle) })
    .getByRole("link", { name: "Ouvrir" })
    .click();

  await expect(page).toHaveURL(/\/etudiant\/examens\/\d+\/$/);
  await expect(page.getByRole("heading", { name: examTitle })).toBeVisible();
  await pause(page);

  await page.locator('textarea[name="code_source"]').fill(
    [
      "public class Main {",
      "  public static void main(String[] args) {",
      "    System.out.println(\"Demo soutenance\");",
      "  }",
      "}",
    ].join("\n")
  );
  await pause(page);
  await page.getByRole("button", { name: "Envoyer" }).click();

  await expect(page).toHaveURL(/\/etudiant\/resultats\/$/);
  await expect(page.getByText("Soumission envoyee. Tests en cours via CI/CD.")).toBeVisible();
  await pause(page, 2000);

  const submissions = await page.evaluate(async () => {
    const response = await fetch("/api/soumissions/", {
      credentials: "same-origin",
    });
    return response.json();
  });
  const submission = submissions
    .filter((item) => item.examen === examId)
    .sort((left, right) => right.id - left.id)[0];

  expect(submission).toBeTruthy();

  const webhookResponse = await request.post(
    "http://127.0.0.1:8000/api/webhook/resultats/",
    {
      headers: {
        "X-API-TOKEN": readWebhookToken(),
      },
      data: {
        soumission: submission.id,
        note: "18.50",
        feedback: "Correction automatique terminee avec succes.",
        statut_soumission: "CORRIGE",
      },
    }
  );
  const webhookStatus = webhookResponse.status();
  expect([200, 201]).toContain(webhookStatus);

  await page.reload();
  await pause(page, 2000);

  await expect(page.getByRole("heading", { name: "Mes resultats" })).toBeVisible();
  const resultRow = page.getByRole("row", { name: new RegExp(examTitle) });
  await expect(resultRow).toBeVisible();
  await expect(resultRow).toContainText("18,50");
  await expect(resultRow).toContainText("Correction automatique terminee avec succes.");
});
