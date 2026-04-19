import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const files = [
  "app/static/ui/base.js",
  "app/static/ui/select.js",
  "app/static/modules/admin-sections.js",
  "app/static/modules/partner-sections.js",
  "app/static/modules/alerts-sections.js",
  "app/static/modules/hourly-sections.js",
  "app/static/modules/entities-sections.js",
  "app/static/admin.js",
  "app/static/partner.js",
  "app/static/hourly.js",
  "app/static/entities.js",
  "app/static/alerts.js",
];

const failures = [];

function sanitizeModuleSource(source) {
  return source
    .replace(/^\s*import\s+[^;]+;\s*$/gmu, "")
    .replace(/^\s*export\s+default\s+/gmu, "")
    .replace(/^\s*export\s+(async\s+function|function|class|const|let|var)\s+/gmu, "$1 ")
    .replace(/^\s*export\s*\{[^}]+\};?\s*$/gmu, "");
}

for (const relativePath of files) {
  const fullPath = path.join(root, relativePath);
  const source = fs.readFileSync(fullPath, "utf8");
  const sanitized = sanitizeModuleSource(source);
  try {
    // eslint-disable-next-line no-new-func
    new Function(sanitized);
  } catch (error) {
    failures.push(`${relativePath}: ${error.message}`);
  }
}

if (failures.length) {
  console.error("Static JS syntax check failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log(`Static JS syntax check passed for ${files.length} files.`);
