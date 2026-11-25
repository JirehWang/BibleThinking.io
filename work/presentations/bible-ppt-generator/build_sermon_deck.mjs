import fs from "node:fs/promises";
import path from "node:path";
import { execFile } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = true;
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
}

function requireArg(args, key) {
  if (!args[key]) {
    throw new Error(`Missing required argument --${key}`);
  }
  return args[key];
}

function parseOptionalInt(value, key) {
  if (value === undefined || value === null || value === false) return null;
  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isFinite(parsed) || parsed <= 0) {
    throw new Error(`Expected --${key} to be a positive integer.`);
  }
  return parsed;
}

function normalizeLine(line) {
  return line.replace(/\r/g, "").trimEnd();
}

function stripMarkdown(value) {
  return value
    .replace(/^\s*[\*\-]\s*/, "")
    .replace(/\*\*/g, "")
    .replace(/^【|】$/g, "")
    .trim();
}

function cleanLabel(value) {
  return stripMarkdown(value).replace(/[：:]\s*$/, "").trim();
}

function splitLabelValue(rawLine) {
  const line = stripMarkdown(rawLine);
  const match = line.match(/^([^:：]+)[:：]\s*(.*)$/);
  if (!match) return null;
  return { label: cleanLabel(match[1]), value: match[2].trim() };
}

function parseSlides(sourceText) {
  const normalized = sourceText.replace(/^\uFEFF/, "");
  const headingRegex = /^###\s*Slide\s+\d+:[^\n]*$/gim;
  const matches = [...normalized.matchAll(headingRegex)];
  const blocks = matches.map((match, index) => {
    const start = match.index ?? 0;
    const end = index + 1 < matches.length ? (matches[index + 1].index ?? normalized.length) : normalized.length;
    return normalized.slice(start, end).trim();
  });
  const slides = [];

  for (const block of blocks) {
    const lines = block.split("\n").map(normalizeLine);
    const heading = lines.find((line) => /^#{2,}\s*Slide\s+\d+/i.test(line));
    if (!heading) continue;

    const titleText = heading.replace(/^#{2,}\s*/i, "").trim();
    const contentIndex = lines.findIndex((line) => /slide content/i.test(line));
    const visualIndex = lines.findIndex((line) => /visual composition/i.test(line));
    const contentLines = contentIndex >= 0
      ? lines.slice(contentIndex + 1, visualIndex >= 0 ? visualIndex : undefined)
      : [];
    const visualLines = visualIndex >= 0 ? lines.slice(visualIndex + 1) : [];

    const items = [];
    let active = null;
    for (const rawLine of contentLines) {
      const line = rawLine.trim();
      if (!line) continue;
      if (!/^[\*\-]/.test(line)) continue;
      const parsed = splitLabelValue(line);
      if (parsed) {
        active = { label: parsed.label, value: parsed.value, children: [] };
        items.push(active);
        continue;
      }
      const child = stripMarkdown(line);
      if (active) {
        active.children.push(child);
      } else {
        items.push({ label: "", value: child, children: [] });
      }
    }

    const visual = {};
    for (const rawLine of visualLines) {
      const line = rawLine.trim();
      if (!line) continue;
      const parsed = splitLabelValue(line);
      if (!parsed) continue;
      const label = parsed.label.toLowerCase();
      if (label.includes("concept")) visual.concept = parsed.value;
      if (label.includes("prompt")) visual.prompt = parsed.value;
    }

    slides.push({
      rawHeading: titleText,
      title: titleText.replace(/^Slide\s+\d+:\s*/i, "").trim(),
      items,
      visual,
    });
  }

  return slides;
}

function summarizeItems(items) {
  return items.map((item) => {
    if (!item.label) return item.value;
    const childText = item.children.length ? ` ${item.children.join(" ")}` : "";
    return `${item.label}: ${item.value}${childText}`.trim();
  });
}

function pickPrimaryQuote(items) {
  for (const item of items) {
    const combined = `${item.label} ${item.value}`.trim();
    if (/經文|金句|主題|大意|信息/i.test(combined)) {
      return item.value || combined;
    }
  }
  return items[0]?.value || "";
}

function pickReference(items) {
  for (const item of items) {
    const combined = `${item.label} ${item.value}`.trim();
    if (/經文|經卷|章節|出處/i.test(combined)) {
      return item.value || combined;
    }
  }
  return "";
}

function truncateText(value, maxChars) {
  if (value.length <= maxChars) return value;
  return `${value.slice(0, Math.max(0, maxChars - 1)).trim()}…`;
}

function titleLayout(title, isCover) {
  const length = title.length;
  if (isCover) {
    if (length > 22) {
      return { fontSize: 38, height: 176, refTop: 264, quoteTop: 316, bulletTop: 456 };
    }
    return { fontSize: 44, height: 150, refTop: 234, quoteTop: 286, bulletTop: 424 };
  }
  if (length > 22) {
    return { fontSize: 29, height: 126, refTop: 184, quoteTop: 234, bulletTop: 360 };
  }
  if (length > 16) {
    return { fontSize: 32, height: 104, refTop: 170, quoteTop: 220, bulletTop: 346 };
  }
  return { fontSize: 35, height: 82, refTop: 156, quoteTop: 206, bulletTop: 332 };
}

function escapeXml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

async function writePromptImageSvg(slide, imagePath) {
  const title = escapeXml(slide.title);
  const prompt = escapeXml(slide.visual.prompt || slide.visual.concept || "Image prompt unavailable");
  const concept = escapeXml(slide.visual.concept || "Visual prompt");
  const bodyLines = [
    prompt.slice(0, 92),
    prompt.slice(92, 184),
    prompt.slice(184, 276),
  ].filter(Boolean);
  const tspanLines = bodyLines
    .map((line, index) => `<tspan x="68" dy="${index === 0 ? 0 : 34}">${escapeXml(line)}</tspan>`)
    .join("");

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" viewBox="0 0 1280 720">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#102542"/>
      <stop offset="52%" stop-color="#153e63"/>
      <stop offset="100%" stop-color="#d0a95a"/>
    </linearGradient>
  </defs>
  <rect width="1280" height="720" fill="url(#bg)"/>
  <circle cx="1040" cy="150" r="130" fill="#ffffff" opacity="0.12"/>
  <circle cx="1180" cy="560" r="210" fill="#ffffff" opacity="0.08"/>
  <rect x="42" y="42" width="1196" height="636" rx="36" fill="#0d1b2a" opacity="0.28" stroke="#f1ddae" stroke-opacity="0.45"/>
  <text x="68" y="116" fill="#f3e9d2" font-size="30" font-family="Microsoft JhengHei, Noto Sans CJK TC, sans-serif" font-weight="700">${title}</text>
  <text x="68" y="168" fill="#ffe4a3" font-size="20" font-family="Microsoft JhengHei, Noto Sans CJK TC, sans-serif">${concept}</text>
  <text x="68" y="276" fill="#ffffff" font-size="30" font-family="Microsoft JhengHei, Noto Sans CJK TC, sans-serif" opacity="0.96">${tspanLines}</text>
  <text x="68" y="616" fill="#f6efd9" font-size="18" font-family="Microsoft JhengHei, Noto Sans CJK TC, sans-serif" opacity="0.92">Auto visual placeholder from Prompt for NotebookLM</text>
  <text x="68" y="648" fill="#f6efd9" font-size="18" font-family="Microsoft JhengHei, Noto Sans CJK TC, sans-serif" opacity="0.70">This block can be replaced later by Bible maps, NotebookLM outputs, or generated artwork.</text>
</svg>`;
  await fs.writeFile(imagePath, svg, "utf8");
  return svg;
}

function svgToDataUrl(svg) {
  return `data:image/svg+xml;base64,${Buffer.from(svg, "utf8").toString("base64")}`;
}

function execFileAsync(file, args) {
  return new Promise((resolve, reject) => {
    execFile(file, args, { windowsHide: true, maxBuffer: 1024 * 1024 * 4 }, (error, stdout, stderr) => {
      if (error) {
        reject(new Error(stderr || stdout || error.message));
        return;
      }
      resolve({ stdout, stderr });
    });
  });
}

async function renderPromptCardPng(scriptPath, imagePath, slide) {
  await execFileAsync("powershell.exe", [
    "-ExecutionPolicy",
    "Bypass",
    "-File",
    scriptPath,
    "-OutputPath",
    imagePath,
    "-Title",
    slide.title,
    "-Concept",
    slide.visual.concept || "Visual prompt",
    "-Prompt",
    slide.visual.prompt || slide.visual.concept || slide.title,
  ]);
  return fs.readFile(imagePath);
}

async function ensureDir(dir) {
  await fs.mkdir(dir, { recursive: true });
}

async function readOptionalJson(filePath) {
  if (!filePath) return null;
  try {
    const raw = await fs.readFile(filePath, "utf8");
    return JSON.parse(raw);
  } catch (error) {
    if (error && error.code === "ENOENT") return null;
    throw error;
  }
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const inputPath = path.resolve(requireArg(args, "input"));
  const outputPath = path.resolve(requireArg(args, "output"));
  const workspace = path.resolve(requireArg(args, "workspace"));
  const skillDir = path.resolve(requireArg(args, "skill-dir"));
  const imageManifestPath = args["image-manifest"] ? path.resolve(args["image-manifest"]) : null;
  const maxSlide = parseOptionalInt(args["max-slide"], "max-slide");
  const sourceText = await fs.readFile(inputPath, "utf8");
  const slidesData = parseSlides(sourceText).filter((slide) => (maxSlide ? Number.parseInt((slide.rawHeading.match(/^Slide\s+(\d+)/i) || [])[1] || "0", 10) <= maxSlide : true));
  const imageManifest = await readOptionalJson(imageManifestPath);

  if (!slidesData.length) {
    throw new Error("No slide blocks were parsed from the input.");
  }

  const tmpDir = path.join(workspace, "tmp");
  const assetDir = path.join(tmpDir, "assets");
  const previewDir = path.join(tmpDir, "preview");
  const qaDir = path.join(tmpDir, "qa");
  await ensureDir(assetDir);
  await ensureDir(previewDir);
  await ensureDir(qaDir);

  const { ensureArtifactToolWorkspace, importArtifactTool, saveBlobToFile } = await import(
    pathToFileURL(path.join(skillDir, "container_tools", "artifact_tool_utils.mjs")).href
  );
  await ensureArtifactToolWorkspace(tmpDir);
  const { Presentation, PresentationFile } = await importArtifactTool(tmpDir);

  const presentation = Presentation.create({
    slideSize: { width: 1280, height: 720 },
  });

  const palette = {
    bg: "#f5efe2",
    ink: "#1f2937",
    muted: "#5f6b7a",
    gold: "#b7883b",
    navy: "#1f3a5f",
    warm: "#efe1bf",
    white: "#ffffff",
  };

  for (let index = 0; index < slidesData.length; index += 1) {
    const slideData = slidesData[index];
    const slide = presentation.slides.add();
    slide.background.fill = palette.bg;

    const contentFrame = { left: 58, top: 48, width: 1164, height: 624 };
    const leftWidth = 500;
    const gap = 34;
    const imageWidth = contentFrame.width - leftWidth - gap;

    const imageSvgPath = path.join(assetDir, `slide-${String(index + 1).padStart(2, "0")}.svg`);
    const imagePngPath = path.join(assetDir, `slide-${String(index + 1).padStart(2, "0")}.png`);
    const scriptPath = path.join(SCRIPT_DIR, "render_prompt_card.ps1");
    await writePromptImageSvg(slideData, imageSvgPath);
    const manifestImagePath = imageManifest?.[String(index + 1)];
    let slideImageBytes;
    let slideImageContentType = "image/png";
    if (manifestImagePath) {
      try {
        slideImageBytes = await fs.readFile(path.resolve(manifestImagePath));
      } catch (error) {
        if (!error || error.code !== "ENOENT") throw error;
      }
    }
    if (!slideImageBytes) {
      slideImageBytes = await renderPromptCardPng(scriptPath, imagePngPath, slideData);
    }

    slide.shapes.add({
      geometry: "rect",
      position: { left: 0, top: 0, width: 1280, height: 720 },
      fill: {
        colorStops: [
          { offset: 0, color: "#fbf8f1" },
          { offset: 100000, color: "#efe4c4" },
        ],
        angle: 45,
        type: "linear",
      },
      line: { style: "solid", fill: "none", width: 0 },
    });

    slide.shapes.add({
      geometry: "roundRect",
      position: { left: contentFrame.left, top: contentFrame.top, width: contentFrame.width, height: contentFrame.height },
      fill: palette.white,
      line: { style: "solid", fill: "#dbc79b", width: 1.4 },
      borderRadius: "rounded-3xl",
      shadow: "shadow-sm",
    });

    const accent = slide.shapes.add({
      geometry: "rect",
      position: { left: contentFrame.left, top: contentFrame.top, width: 14, height: contentFrame.height },
      fill: palette.gold,
      line: { style: "solid", fill: "none", width: 0 },
    });
    accent.name = `accent-${index + 1}`;

    const isCover = index === 0;
    const layout = titleLayout(slideData.title, isCover);

    const titleBox = slide.shapes.add({
      geometry: "textbox",
      position: { left: 92, top: 82, width: 442, height: layout.height },
      fill: "none",
      line: { style: "solid", fill: "none", width: 0 },
      name: `title-${index + 1}`,
    });
    titleBox.text = slideData.title;
    titleBox.text.style = {
      fontSize: layout.fontSize,
      bold: true,
      color: palette.navy,
      fontFace: "Microsoft JhengHei",
    };

    const referenceText = pickReference(slideData.items) || slideData.rawHeading;
    const refBox = slide.shapes.add({
      geometry: "textbox",
      position: { left: 92, top: layout.refTop, width: 420, height: 36 },
      fill: "none",
      line: { style: "solid", fill: "none", width: 0 },
      name: `ref-${index + 1}`,
    });
    refBox.text = referenceText;
    refBox.text.style = {
      fontSize: 18,
      color: palette.gold,
      bold: true,
      fontFace: "Microsoft JhengHei",
    };

    const quote = pickPrimaryQuote(slideData.items);
    if (quote) {
      const quoteBox = slide.shapes.add({
        geometry: "roundRect",
        position: { left: 92, top: layout.quoteTop, width: 420, height: isCover ? 116 : 102 },
        fill: palette.warm,
        line: { style: "solid", fill: "#d9c086", width: 1 },
        borderRadius: "rounded-2xl",
        name: `quote-${index + 1}`,
      });
      quoteBox.text = quote;
      quoteBox.text.style = {
        fontSize: isCover ? 19 : 18,
        color: palette.ink,
        italic: true,
        fontFace: "Microsoft JhengHei",
      };
    }

    const bullets = summarizeItems(slideData.items)
      .slice(0, isCover ? 3 : 5)
      .map((text) => truncateText(text, isCover ? 92 : 108));
    const bulletTop = layout.bulletTop;
    for (let bulletIndex = 0; bulletIndex < bullets.length; bulletIndex += 1) {
      const y = bulletTop + bulletIndex * 56;
      const bulletText = bullets[bulletIndex];
      const bulletFontSize = bulletText.length > 72 ? 17 : 19;
      slide.shapes.add({
        geometry: "ellipse",
        position: { left: 96, top: y + 10, width: 12, height: 12 },
        fill: palette.gold,
        line: { style: "solid", fill: "none", width: 0 },
      });
      const bulletBox = slide.shapes.add({
        geometry: "textbox",
        position: { left: 122, top: y, width: 394, height: 48 },
        fill: "none",
        line: { style: "solid", fill: "none", width: 0 },
        name: `bullet-${index + 1}-${bulletIndex + 1}`,
      });
      bulletBox.text = bulletText;
      bulletBox.text.style = {
        fontSize: bulletFontSize,
        color: palette.ink,
        fontFace: "Microsoft JhengHei",
      };
    }

    slide.shapes.add({
      geometry: "roundRect",
      position: {
        left: contentFrame.left + leftWidth + gap,
        top: 92,
        width: imageWidth,
        height: 484,
      },
      fill: "#0d1b2a",
      line: { style: "solid", fill: palette.navy, width: 1.2 },
      borderRadius: "rounded-3xl",
      name: `image-frame-${index + 1}`,
    });

    const image = slide.images.add({
      blob: slideImageBytes,
      contentType: slideImageContentType,
      prompt: slideData.visual.prompt || slideData.visual.concept || slideData.title,
      alt: slideData.visual.concept || slideData.title,
      fit: "cover",
      geometry: "roundRect",
      borderRadius: "rounded-3xl",
      position: {
        left: contentFrame.left + leftWidth + gap + 8,
        top: 100,
        width: imageWidth - 16,
        height: 468,
      },
    });

    const conceptBox = slide.shapes.add({
      geometry: "textbox",
      position: { left: contentFrame.left + leftWidth + gap + 20, top: 592, width: imageWidth - 40, height: 42 },
      fill: "none",
      line: { style: "solid", fill: "none", width: 0 },
      name: `concept-${index + 1}`,
    });
    conceptBox.text = slideData.visual.concept || "Visual direction";
    conceptBox.text.style = {
      fontSize: 17,
      color: palette.muted,
      fontFace: "Microsoft JhengHei",
      italic: true,
    };

    const pageBox = slide.shapes.add({
      geometry: "textbox",
      position: { left: 1116, top: 618, width: 80, height: 24 },
      fill: "none",
      line: { style: "solid", fill: "none", width: 0 },
      name: `page-${index + 1}`,
    });
    pageBox.text = `${index + 1}`.padStart(2, "0");
    pageBox.text.style = {
      fontSize: 16,
      color: palette.gold,
      bold: true,
      alignment: "right",
      fontFace: "Microsoft JhengHei",
    };
  }

  await ensureDir(path.dirname(outputPath));
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);

  for (const [index, slide] of presentation.slides.items.entries()) {
    const png = await presentation.export({ slide, format: "png", scale: 1 });
    await saveBlobToFile(png, path.join(previewDir, `slide-${String(index + 1).padStart(2, "0")}.png`));
  }
  const montage = await presentation.export({ format: "webp", montage: true, scale: 1 });
  await saveBlobToFile(montage, path.join(qaDir, "deck-montage.webp"));

  const manifest = {
    slideCount: slidesData.length,
    inputPath,
    outputPath,
    previewDir,
    qaDir,
    generatedAt: new Date().toISOString(),
  };
  await fs.writeFile(path.join(workspace, "tmp", "manifest.json"), JSON.stringify(manifest, null, 2), "utf8");
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
