import { expect } from "@playwright/test";
import { test } from "./fixtures";

const OPEN_BROWSER = {
  open: true,
  url: "https://www.selenium.dev/selenium/web/web-form.html",
  title: "Web form",
  status: "open",
  last_action: "select",
  last_result: "ok",
  last_error: "",
  screenshot_data_url: "",
  updated_at: "2026-07-31T02:00:00Z",
  controls: [],
  always_allow_reads: true,
  allowed_domains: [],
  history: [],
  evidence: [],
  media: [],
  streaming_media: [],
  streaming_media_status: "idle",
  streaming_media_error: "",
  streaming_media_progress: {},
  pending_action: {},
  control_owner: "agent",
  control_changed_at: null,
};

test("an active Secure Browser remains recoverable after the side panel is hidden", async ({
  page,
}) => {
  await page.route("**/v1/browser/state?**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(OPEN_BROWSER),
    }),
  );
  await page.goto("/");

  await expect(page.getByText("Isolated session active")).toBeVisible();
  await page.getByRole("button", { name: "Hide side panel" }).click();

  const browserButton = page.getByRole("button", { name: "Browser", exact: true });
  await expect(browserButton).toBeVisible();
  await expect(browserButton).toHaveAttribute("title", "Show the active Secure Browser");

  await browserButton.click();
  await expect(page.getByText("Isolated session active")).toBeVisible();
  await expect(page.getByText("Web form", { exact: true })).toBeVisible();
});

test("the user can take control of the active browser and return it to the agent", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1600, height: 1000 });
  let owner: "agent" | "user" = "agent";
  const actions: Array<Record<string, unknown>> = [];
  const browserState = () => ({
    ...OPEN_BROWSER,
    control_owner: owner,
    control_changed_at: owner === "user" ? "2026-07-31T02:01:00Z" : null,
    screenshot_data_url:
      "data:image/svg+xml;base64," +
      Buffer.from(
        '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="900"><rect width="1280" height="900" fill="#fff"/><rect x="120" y="100" width="240" height="80" fill="#4f8cff"/></svg>',
      ).toString("base64"),
  });
  await page.route("**/v1/browser/state?**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(browserState()),
    }),
  );
  await page.route("**/v1/browser/screenshot?**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, ...browserState() }),
    }),
  );
  await page.route("**/v1/browser/control?**", async (route) => {
    const body = route.request().postDataJSON();
    owner = body.owner;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, control_owner: owner }),
    });
  });
  await page.route("**/v1/browser/human-action?**", async (route) => {
    actions.push(route.request().postDataJSON());
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ok: true, ...browserState() }),
    });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Take control" }).click();

  const dialog = page.getByRole("dialog", { name: "Interactive Secure Browser" });
  await expect(dialog).toBeVisible();
  await expect(page.getByText("You are in control")).toBeVisible();
  await expect.poll(async () => {
    const box = await dialog.boundingBox();
    return { width: Math.round(box?.width || 0), height: Math.round(box?.height || 0) };
  }).toEqual({ width: 1480, height: 960 });
  await expect(dialog).toHaveCSS("resize", "both");
  await page.getByRole("button", { name: "Maximize browser" }).click();
  await expect.poll(async () => {
    const box = await dialog.boundingBox();
    return { width: Math.round(box?.width || 0), height: Math.round(box?.height || 0) };
  }).toEqual({ width: 1584, height: 984 });
  await page.getByRole("button", { name: "Restore browser size" }).click();
  await expect(dialog).toHaveCSS("resize", "both");

  await page.setViewportSize({ width: 680, height: 900 });
  await expect(dialog).toHaveCSS("resize", "both");
  await expect(page.getByRole("button", { name: "Maximize browser" })).toBeVisible();
  await expect(page.getByText("Resize from the striped corner, or use Maximize.")).toBeVisible();
  const canvas = page.locator(".browser-control-canvas");
  const preview = page.getByRole("img", { name: "Interactive browser preview" });
  await expect.poll(async () => {
    const dialogBox = await dialog.boundingBox();
    const canvasBox = await canvas.boundingBox();
    const previewBox = await preview.boundingBox();
    if (!dialogBox || !canvasBox || !previewBox) return false;
    return (
      dialogBox.y >= 0 &&
      dialogBox.y + dialogBox.height <= 900 &&
      previewBox.x >= canvasBox.x &&
      previewBox.y >= canvasBox.y &&
      previewBox.x + previewBox.width <= canvasBox.x + canvasBox.width + 1 &&
      previewBox.y + previewBox.height <= canvasBox.y + canvasBox.height + 1
    );
  }).toBe(true);

  await page.getByRole("img", { name: "Interactive browser preview" }).click({
    position: { x: 100, y: 80 },
  });
  await page.getByRole("textbox", { name: "Text to type into the focused browser field" }).fill("Two");
  await page.getByRole("button", { name: "Type", exact: true }).click();
  await page.getByRole("button", { name: "Scroll down" }).click();

  await expect.poll(() => actions.map((action) => action.action)).toEqual([
    "click",
    "type",
    "scroll",
  ]);
  await page.getByRole("button", { name: "Return to agent" }).click();
  await expect(page.getByRole("dialog", { name: "Interactive Secure Browser" })).toBeHidden();
  expect(owner).toBe("agent");
});
