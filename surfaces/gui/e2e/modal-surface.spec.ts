import { expect } from "@playwright/test";
import { test } from "./fixtures";

test("modal and field surfaces stay opaque in light and dark themes", async ({ page }) => {
  await page.goto("/");

  const surfaces = await page.evaluate(() => {
    const modal = document.createElement("section");
    modal.className = "research-modal";
    const browser = document.createElement("section");
    browser.className = "browser-control-modal";
    document.body.append(modal, browser);

    const light = [getComputedStyle(modal).backgroundColor, getComputedStyle(browser).backgroundColor];
    const originalTheme = document.documentElement.dataset.theme;
    document.documentElement.dataset.theme = "dark";
    const dark = [getComputedStyle(modal).backgroundColor, getComputedStyle(browser).backgroundColor];

    if (originalTheme) document.documentElement.dataset.theme = originalTheme;
    else delete document.documentElement.dataset.theme;
    modal.remove();
    browser.remove();
    return { light, dark };
  });

  expect(surfaces.light).toEqual(["rgb(255, 255, 255)", "rgb(255, 255, 255)"]);
  expect(surfaces.dark).toEqual(["rgb(28, 30, 34)", "rgb(28, 30, 34)"]);
});
