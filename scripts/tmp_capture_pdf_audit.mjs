import fs from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const htmlPath = path.resolve("doc/defense_presentation_audit.html").replace(/\\/g, "/");
const outDir = "doc/screenshots/pdf_audit";
fs.mkdirSync(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
try {
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 }, deviceScaleFactor: 1 });
  await page.goto(`file:///${htmlPath}`);
  await page.evaluate(() => {
    for (const slide of document.querySelectorAll(".slide")) {
      const content = slide.querySelector(".slide-content");
      content.style.transform = "scale(1)";
      content.style.width = "100%";
      const scale = Math.min(1, slide.clientWidth / content.scrollWidth, slide.clientHeight / content.scrollHeight);
      if (scale < 1) {
        const applied = Math.max(0.62, scale);
        content.style.transform = `scale(${applied.toFixed(4)})`;
        content.style.width = `${(100 / applied).toFixed(2)}%`;
      }
    }
  });
  const data = [];
  const slides = await page.$$(".slide");
  for (const [index, slide] of slides.entries()) {
    const slideNo = String(index + 1).padStart(2, "0");
    await slide.screenshot({ path: `${outDir}/slide_${slideNo}.png` });
    const info = await slide.evaluate((node) => {
      const content = node.querySelector(".slide-content");
      const rect = content.getBoundingClientRect();
      return { scale: getComputedStyle(content).transform, height: rect.height };
    });
    data.push({ slide: index + 1, ...info });
  }
  console.log(JSON.stringify(data));
} finally {
  await browser.close();
}
