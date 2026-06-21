import fs from "node:fs/promises";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { chromium } from "playwright";

const usage = `Usage:
  node scripts/render_markdown_pdf.mjs [input.md] [output.pdf] [options]

Defaults:
  input.md   doc/presentations/defense_presentation.md
  output.pdf doc/defense_presentation.pdf

Options:
  --html <path>          Also write the rendered HTML to this path.
  --keep-html           Keep the temporary HTML next to the PDF.
  --title <text>        HTML document title.
  --format <format>     PDF format for Chromium, default: A4.
  --font-scale <number> Presentation/readability scale, default: 1.
  --strip-emoji         Remove emoji/symbol pictographs before PDF rendering.
  --slides              Render h2 sections as 16:9 presentation slides.
  --portrait            Render portrait pages.
  --landscape           Render landscape pages, default.
  --margin <css-value>  CSS @page margin, default: 14mm 15mm.
  --help                Show this help.
`;

const root = process.cwd();

const parseArgs = (argv) => {
  const positional = [];
  const options = {
    format: "A4",
    landscape: true,
    margin: "14mm 15mm",
    title: "Markdown PDF",
    keepHtml: false,
    htmlPath: null,
    fontScale: 1,
    stripEmoji: false,
    slides: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--help" || arg === "-h") {
      options.help = true;
    } else if (arg === "--portrait") {
      options.landscape = false;
    } else if (arg === "--landscape") {
      options.landscape = true;
    } else if (arg === "--keep-html") {
      options.keepHtml = true;
    } else if (arg === "--html") {
      options.htmlPath = argv[++i];
    } else if (arg === "--title") {
      options.title = argv[++i];
    } else if (arg === "--format") {
      options.format = argv[++i];
    } else if (arg === "--font-scale") {
      options.fontScale = Number(argv[++i]);
      if (!Number.isFinite(options.fontScale) || options.fontScale <= 0) {
        throw new Error("--font-scale must be a positive number");
      }
    } else if (arg === "--strip-emoji") {
      options.stripEmoji = true;
    } else if (arg === "--slides") {
      options.slides = true;
      options.landscape = true;
    } else if (arg === "--margin") {
      options.margin = argv[++i];
    } else if (arg.startsWith("--")) {
      throw new Error(`Unknown option: ${arg}`);
    } else {
      positional.push(arg);
    }
  }

  const inputPath = positional[0] ?? path.join("doc", "presentations", "defense_presentation.md");
  const outputPath = positional[1] ?? path.join("doc", "defense_presentation.pdf");
  return {
    ...options,
    inputPath: path.resolve(root, inputPath),
    outputPath: path.resolve(root, outputPath),
  };
};

const escapeHtml = (value) =>
  value
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");

const escapeAttribute = (value) => escapeHtml(value).replaceAll('"', "&quot;");

const stripEmoji = (value) =>
  value
    .replace(/[→↔⇒➜➝➞]/g, "->")
    .replace(/[✅✔✓☑]/g, "Да")
    .replace(/[❌✖✗☒]/g, "Нет")
    .replace(/[⚠]/g, "Внимание:")
    .replace(/[①②③④⑤⑥⑦⑧⑨⑩]/g, "")
    .replace(/\p{Extended_Pictographic}/gu, "")
    .replace(/[\u2190-\u21FF\u2300-\u23FF\u2460-\u24FF\u25A0-\u27BF\u2900-\u297F\u2B00-\u2BFF]/gu, "")
    .replace(/[\u{1F000}-\u{1FAFF}\uFE0F\u200D]/gu, "")
    .replace(/[ \t]{2,}/g, " ")
    .trim();

const inline = (value, options) => {
  const source = options.stripEmoji ? stripEmoji(value) : value;
  let rendered = escapeHtml(source);
  rendered = rendered.replace(/`([^`]+)`/g, "<code>$1</code>");
  rendered = rendered.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  rendered = rendered.replace(/\*([^*]+)\*/g, "<em>$1</em>");
  rendered = rendered.replace(
    /!\[([^\]]*)\]\(([^)]+)\)/g,
    (_match, alt, src) => `<img src="${escapeAttribute(src)}" alt="${escapeAttribute(alt)}">`,
  );
  rendered = rendered.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    (_match, label, href) => `<a href="${escapeAttribute(href)}">${label}</a>`,
  );
  return rendered;
};

const isTableSeparator = (line) =>
  /^\s*\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(line);

const splitTableRow = (line) =>
  line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());

const renderMarkdown = (source, options) => {
  const lines = source.replace(/\r\n/g, "\n").split("\n");
  const html = [];
  let paragraph = [];
  let list = null;
  let inCode = false;
  let codeLang = "";
  let code = [];
  let inBlockquote = false;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    html.push(`<p>${inline(paragraph.join(" "), options)}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (!list) return;
    html.push(`</${list}>`);
    list = null;
  };

  const closeBlockquote = () => {
    if (!inBlockquote) return;
    flushParagraph();
    html.push("</blockquote>");
    inBlockquote = false;
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];

    if (inCode) {
      if (line.startsWith("```")) {
        const cls = codeLang ? ` class="language-${escapeAttribute(codeLang)}"` : "";
        const codeText = options.stripEmoji ? stripEmoji(code.join("\n")) : code.join("\n");
        html.push(`<pre${cls}><code>${escapeHtml(codeText)}</code></pre>`);
        inCode = false;
        codeLang = "";
        code = [];
      } else {
        code.push(line);
      }
      continue;
    }

    if (line.startsWith("```")) {
      closeBlockquote();
      flushParagraph();
      flushList();
      inCode = true;
      codeLang = line.slice(3).trim();
      continue;
    }

    if (/^\s*$/.test(line)) {
      flushParagraph();
      flushList();
      closeBlockquote();
      continue;
    }

    if (/^\s*---+\s*$/.test(line)) {
      closeBlockquote();
      flushParagraph();
      flushList();
      html.push("<hr>");
      continue;
    }

    if (line.startsWith(">")) {
      flushList();
      if (!inBlockquote) {
        flushParagraph();
        html.push("<blockquote>");
        inBlockquote = true;
      }
      paragraph.push(line.replace(/^>\s?/, ""));
      continue;
    }

    closeBlockquote();

    const heading = /^(#{1,6})\s+(.*)$/.exec(line);
    if (heading) {
      flushParagraph();
      flushList();
      const level = heading[1].length;
      html.push(`<h${level}>${inline(heading[2], options)}</h${level}>`);
      continue;
    }

    if (
      line.includes("|") &&
      i + 1 < lines.length &&
      lines[i + 1].includes("|") &&
      isTableSeparator(lines[i + 1])
    ) {
      flushParagraph();
      flushList();
      const header = splitTableRow(line);
      html.push("<table><thead><tr>");
      html.push(header.map((cell) => `<th>${inline(cell, options)}</th>`).join(""));
      html.push("</tr></thead><tbody>");
      i += 2;
      while (i < lines.length && lines[i].includes("|") && !/^\s*$/.test(lines[i])) {
        const row = splitTableRow(lines[i]);
        html.push("<tr>");
        html.push(row.map((cell) => `<td>${inline(cell, options)}</td>`).join(""));
        html.push("</tr>");
        i += 1;
      }
      i -= 1;
      html.push("</tbody></table>");
      continue;
    }

    const bullet = /^\s*[-*]\s+(.*)$/.exec(line);
    const ordered = /^\s*\d+\.\s+(.*)$/.exec(line);
    if (bullet || ordered) {
      flushParagraph();
      const wanted = bullet ? "ul" : "ol";
      if (list !== wanted) {
        flushList();
        html.push(`<${wanted}>`);
        list = wanted;
      }
      html.push(`<li>${inline((bullet || ordered)[1], options)}</li>`);
      continue;
    }

    if (/^!\[/.test(line.trim())) {
      flushParagraph();
      flushList();
      html.push(`<figure>${inline(line.trim(), options)}</figure>`);
      continue;
    }

    paragraph.push(line.trim());
  }

  flushParagraph();
  flushList();
  closeBlockquote();
  return html.join("\n");
};

const buildCss = ({ margin, landscape, fontScale }) => {
  const scaled = (value) => `${(value * fontScale).toFixed(2)}px`;
  return `
@page {
  size: A4 ${landscape ? "landscape" : "portrait"};
  margin: ${margin};
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: #17201c;
  background: #ffffff;
  font-family: "Segoe UI", "Arial", sans-serif;
  font-size: ${scaled(12.5)};
  line-height: 1.42;
}
main { max-width: ${landscape ? "1080px" : "760px"}; margin: 0 auto; }
h1, h2, h3 { color: #12362b; line-height: 1.15; margin: 0.45em 0 0.35em; }
h1 { font-size: ${scaled(30)}; border-bottom: 3px solid #2f8f67; padding-bottom: 8px; }
h2 { font-size: ${scaled(24)}; page-break-before: always; break-before: page; }
h1 + blockquote + figure + hr + h2,
h1 + blockquote + figure + hr,
h2:first-of-type { page-break-before: auto; break-before: auto; }
h3 { font-size: ${scaled(17)}; margin-top: 0.75em; }
p { margin: 0.35em 0 0.55em; }
blockquote {
  margin: 10px 0 12px;
  padding: 8px 14px;
  border-left: 5px solid #2f8f67;
  background: #edf7f2;
}
ul, ol { margin: 0.25em 0 0.7em 1.35em; padding: 0; }
li { margin: 0.18em 0; }
img {
  display: block;
  max-width: 100%;
  max-height: ${landscape ? "132mm" : "190mm"};
  object-fit: contain;
  margin: 8px auto 12px;
  border-radius: 8px;
}
figure { margin: 0.35em 0 0.75em; page-break-inside: avoid; break-inside: avoid; }
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #111827;
  color: #e5f3ec;
  border-radius: 8px;
  padding: 10px 12px;
  font-size: ${scaled(9.2)};
  line-height: 1.25;
  page-break-inside: avoid;
  break-inside: avoid;
}
code {
  font-family: "Cascadia Mono", "Consolas", monospace;
  background: #eef3f0;
  padding: 1px 4px;
  border-radius: 4px;
}
pre code { background: transparent; padding: 0; border-radius: 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 8px 0 12px;
  font-size: ${scaled(10)};
  page-break-inside: avoid;
  break-inside: avoid;
}
th, td { border: 1px solid #cdd8d2; padding: 5px 7px; vertical-align: top; }
th { background: #e5f2ec; color: #12362b; }
hr { border: 0; border-top: 1px solid #d5e2dc; margin: 14px 0; }
a { color: #206f51; text-decoration: none; }
`;
};

const splitSlideSections = (markdown) => {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const cover = [];
  const sections = [];
  let current = cover;

  for (const line of lines) {
    if (/^##\s+Слайд\s+\d+/u.test(line)) {
      current = [line];
      sections.push(current);
    } else if (sections.length === 0) {
      if (!/^##\s+Оглавление/u.test(line) && current !== null) {
        cover.push(line);
      } else {
        current = null;
      }
    } else {
      current.push(line);
    }
  }

  return [cover.join("\n"), ...sections.map((section) => section.join("\n"))]
    .map((section) => section.trim())
    .filter(Boolean);
};

const buildSlidesCss = ({ fontScale }) => {
  const scaled = (value) => `${(value * fontScale).toFixed(2)}px`;
  return `
@page { size: 13.333in 7.5in; margin: 0; }
* { box-sizing: border-box; }
html, body {
  margin: 0;
  padding: 0;
  background: #ffffff;
  color: #17201c;
  font-family: Arial, "Liberation Sans", sans-serif;
}
.slide {
  position: relative;
  width: 13.333in;
  height: 7.5in;
  padding: 0.42in 0.52in;
  page-break-after: always;
  break-after: page;
  overflow: hidden;
  background: #ffffff;
}
.slide::after {
  content: "";
  position: absolute;
  left: 0.52in;
  right: 0.52in;
  bottom: 0.24in;
  height: 2px;
  background: #d5e2dc;
}
.slide-content {
  width: 100%;
  height: 100%;
  transform-origin: top left;
}
h1, h2, h3 {
  color: #12362b;
  line-height: 1.12;
  margin: 0 0 0.18in;
}
h1 { font-size: ${scaled(34)}; border-bottom: 4px solid #2f8f67; padding-bottom: 0.1in; }
h2 { font-size: ${scaled(31)}; border-bottom: 3px solid #2f8f67; padding-bottom: 0.08in; }
h3 { font-size: ${scaled(19)}; margin-top: 0.12in; margin-bottom: 0.06in; }
p, li, td, th {
  font-size: ${scaled(15)};
  line-height: 1.28;
}
p { margin: 0 0 0.07in; }
ul, ol { margin: 0.04in 0 0.1in 0.22in; padding: 0; }
li { margin: 0.02in 0; }
blockquote {
  margin: 0.08in 0 0.12in;
  padding: 0.1in 0.14in;
  border-left: 5px solid #2f8f67;
  background: #edf7f2;
}
figure { margin: 0.08in 0 0.12in; }
img {
  display: block;
  max-width: 100%;
  max-height: 3.35in;
  object-fit: contain;
  margin: 0.04in auto 0.1in;
  border-radius: 6px;
}
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  background: #111827;
  color: #e5f3ec;
  border-radius: 8px;
  padding: 0.1in 0.14in;
  font-family: "Courier New", monospace;
  font-size: ${scaled(10)};
  line-height: 1.18;
  margin: 0.06in 0 0.12in;
}
code {
  font-family: "Courier New", monospace;
  background: #eef3f0;
  padding: 1px 4px;
  border-radius: 4px;
}
pre code { background: transparent; padding: 0; border-radius: 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.06in 0 0.1in;
}
th, td {
  border: 1px solid #cdd8d2;
  padding: 0.045in 0.06in;
  vertical-align: top;
}
th { background: #e5f2ec; color: #12362b; }
hr { border: 0; border-top: 1px solid #d5e2dc; margin: 0.1in 0; }
a { color: #206f51; text-decoration: none; }
`;
};

const slideFitScript = `
(() => {
  for (const slide of document.querySelectorAll(".slide")) {
    const content = slide.querySelector(".slide-content");
    if (!content) continue;
    content.style.transform = "scale(1)";
    content.style.width = "100%";
    const availableW = slide.clientWidth - 0;
    const availableH = slide.clientHeight - 0;
    const scale = Math.min(1, availableW / content.scrollWidth, availableH / content.scrollHeight);
    if (scale < 1) {
      content.style.transform = "scale(" + Math.max(0.62, scale).toFixed(4) + ")";
      content.style.width = (100 / Math.max(0.62, scale)).toFixed(2) + "%";
    }
  }
})();
`;

const buildSlidesHtml = (markdown, options) => {
  const slides = splitSlideSections(markdown)
    .map((section) => `<section class="slide"><div class="slide-content">${renderMarkdown(section, options)}</div></section>`)
    .join("\n");

  return `<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(options.title)}</title>
  <style>${buildSlidesCss(options)}</style>
</head>
<body>
  ${slides}
  <script>${slideFitScript}</script>
</body>
</html>
`;
};

const buildHtml = (markdown, options) => `<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <title>${escapeHtml(options.title)}</title>
  <style>${buildCss(options)}</style>
</head>
<body>
  <main>${renderMarkdown(markdown, options)}</main>
</body>
</html>
`;

const renderPdf = async (options) => {
  const markdown = await fs.readFile(options.inputPath, "utf8");
  const html = options.slides ? buildSlidesHtml(markdown, options) : buildHtml(markdown, options);
  const htmlPath = path.resolve(
    root,
    options.htmlPath ??
      path.join(
        path.dirname(options.outputPath),
        `${path.basename(options.outputPath, path.extname(options.outputPath))}.html`,
      ),
  );

  await fs.mkdir(path.dirname(options.outputPath), { recursive: true });
  await fs.mkdir(path.dirname(htmlPath), { recursive: true });
    await fs.writeFile(htmlPath, html, "utf8");
  const tempPdfPath = `${options.outputPath}.tmp-${Date.now()}.pdf`;

  try {
    const browser = await chromium.launch({ headless: true });
    try {
      const page = await browser.newPage({ viewport: { width: 1600, height: 1000 } });
      await page.goto(pathToFileURL(htmlPath).href, { waitUntil: "networkidle" });
      if (options.slides) {
        await page.evaluate(slideFitScript);
      }
      await page.pdf({
        path: tempPdfPath,
        ...(options.slides ? { width: "13.333in", height: "7.5in" } : { format: options.format }),
        landscape: options.landscape,
        printBackground: true,
        preferCSSPageSize: true,
      });
    } finally {
      await browser.close();
    }

    await fs.rm(options.outputPath, { force: true });
    await fs.rename(tempPdfPath, options.outputPath);
  } finally {
    if (!options.keepHtml && !options.htmlPath) {
      await fs.rm(htmlPath, { force: true });
    }
    await fs.rm(tempPdfPath, { force: true });
  }

  const stat = await fs.stat(options.outputPath);
  console.log(`Rendered ${path.relative(root, options.outputPath)} (${stat.size} bytes)`);
};

try {
  const options = parseArgs(process.argv.slice(2));
  if (options.help) {
    console.log(usage);
  } else {
    await renderPdf(options);
  }
} catch (error) {
  if (error?.code === "EBUSY" || error?.code === "EPERM") {
    console.error(`${error.message}\nClose the target PDF if it is open, then run the command again.`);
  } else {
    console.error(error.message);
  }
  console.error(usage);
  process.exit(1);
}
