import fs from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { FileBlob, SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = new URL("../", import.meta.url);
const dataset = JSON.parse(await fs.readFile(new URL("examples/small-school.json", root), "utf8"));
const workbook = Workbook.create();

const guide = workbook.worksheets.add("Guide");
guide.showGridLines = false;
guide.getRange("A1:F1").merge();
guide.getRange("A1").values = [["ScheduleGenerator school data import"]];
guide.getRange("A1:F1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF", size: 18 }, rowHeight: 32, verticalAlignment: "center" };
guide.getRange("A3:B8").values = [
  ["Step", "Action"],
  [1, "Open the Dataset worksheet."],
  [2, "Edit JSON only in value_json. Keep every section name unique."],
  [3, "Save as .xlsx and run the import command in preview mode."],
  [4, "Correct every reported row or field error."],
  [5, "Apply the same file only after the preview is valid."],
];
guide.getRange("A3:B3").format = { fill: "#D9EAF7", font: { bold: true, color: "#17365D" } };
guide.getRange("A3:B8").format.borders = { preset: "all", style: "thin", color: "#B4C7E7" };
guide.getRange("A10:F11").merge(true);
guide.getRange("A10:A11").values = [["Important: import is atomic. Invalid data is never partially saved."], ["The template contains synthetic demonstration data and no personal information."]];
guide.getRange("A10:F11").format = { fill: "#FFF2CC", font: { color: "#7F6000" }, wrapText: true };
guide.getRange("A1:F14").format.autofitRows();
guide.getRange("A:A").format.columnWidth = 18;
guide.getRange("B:B").format.columnWidth = 72;
guide.freezePanes.freezeRows(1);

const sheet = workbook.worksheets.add("Dataset");
sheet.showGridLines = false;
const rows = Object.entries(dataset).map(([section, value]) => [section, JSON.stringify(value)]);
sheet.getRangeByIndexes(0, 0, rows.length + 1, 2).values = [["section", "value_json"], ...rows];
sheet.getRange("A1:B1").format = { fill: "#17365D", font: { bold: true, color: "#FFFFFF" }, rowHeight: 26 };
sheet.getRangeByIndexes(0, 0, rows.length + 1, 2).format.borders = { preset: "all", style: "thin", color: "#D9E2F3" };
sheet.getRangeByIndexes(1, 1, rows.length, 1).format = { wrapText: true, verticalAlignment: "top" };
sheet.getRangeByIndexes(1, 0, rows.length, 1).format.font = { bold: true, color: "#17365D" };
sheet.getRange("A:A").format.columnWidth = 28;
sheet.getRange("B:B").format.columnWidth = 110;
sheet.getRangeByIndexes(1, 0, rows.length, 2).format.rowHeight = 45;
sheet.freezePanes.freezeRows(1);
sheet.freezePanes.freezeColumns(1);

const outputDir = new URL("outputs/stage-7/", root);
await fs.mkdir(outputDir, { recursive: true });
const outputUrl = new URL("school-data-import-template.xlsx", outputDir);
const previewDir = process.argv[2];
if (previewDir) {
  await fs.mkdir(previewDir, { recursive: true });
  try {
    const existing = await SpreadsheetFile.importXlsx(await FileBlob.load(fileURLToPath(outputUrl)));
    const preview = await existing.render({ sheetName: "Guide", autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(`${previewDir}/existing-guide.png`, new Uint8Array(await preview.arrayBuffer()));
  } catch (error) {
    if (error?.code !== "ENOENT") throw error;
  }
}
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(fileURLToPath(outputUrl));

if (previewDir) {
  for (const name of ["Guide", "Dataset"]) {
    const preview = await workbook.render({ sheetName: name, autoCrop: "all", scale: 1, format: "png" });
    await fs.writeFile(`${previewDir}/${name.toLowerCase()}.png`, new Uint8Array(await preview.arrayBuffer()));
  }
  const inspection = await workbook.inspect({ kind: "table", range: "Dataset!A1:B8", include: "values,formulas", tableMaxRows: 8, tableMaxCols: 2 });
  const formulaErrors = await workbook.inspect({ kind: "match", searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A", options: { useRegex: true, maxResults: 50 }, summary: "final formula error scan" });
  console.log(inspection.ndjson);
  console.log(formulaErrors.ndjson);
}
