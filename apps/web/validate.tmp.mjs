import { readFileSync } from "node:fs";
import { accessScoreResult } from "@rio-preto/domain";
accessScoreResult.parse(JSON.parse(readFileSync("public/data/acesso/metrics.json", "utf8")));
console.log("acesso artifact valid");
