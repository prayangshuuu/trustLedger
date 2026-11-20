// Copies the public docs site (docs/site) and its figures into public/docs so it ships at /docs.
import { cpSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../../../", import.meta.url).pathname;
const out = new URL("../public/docs/", import.meta.url).pathname;
rmSync(out, { recursive: true, force: true });
mkdirSync(join(out, "figures"), { recursive: true });
mkdirSync(join(out, "media"), { recursive: true });
cpSync(join(root, "docs/site/index.html"), join(out, "index.html"));
for (const [dir, target] of [["training_files", "figures"], ["docs/media", "media"]]) {
  for (const f of readdirSync(join(root, dir)).filter((n) => n.endsWith(".png"))) {
    cpSync(join(root, dir, f), join(out, target, f));
  }
}
console.log("docs site copied to public/docs");
