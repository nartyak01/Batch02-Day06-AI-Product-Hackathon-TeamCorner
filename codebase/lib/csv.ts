import { promises as fs } from "fs";
import path from "path";

export const dataDir = path.join(process.cwd(), "data");

export function parseCsv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let cell = "";
  let row: string[] = [];
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];

    if (char === '"' && inQuotes && next === '"') {
      cell += '"';
      index += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
      row.push(cell);
      if (row.some((value) => value.length > 0)) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += char;
    }
  }

  if (cell.length > 0 || row.length > 0) {
    row.push(cell);
    rows.push(row);
  }

  const [headers = [], ...body] = rows;
  return body.map((values) =>
    Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]))
  );
}

export function serializeCsv(rows: Record<string, string>[], headers: string[]): string {
  const lines = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => escapeCsv(row[header] ?? "")).join(","))
  ];
  return `${lines.join("\n")}\n`;
}

export async function readCsv<T extends Record<string, string>>(fileName: string): Promise<T[]> {
  const filePath = path.join(dataDir, fileName);
  const text = await fs.readFile(filePath, "utf8");
  return parseCsv(text) as T[];
}

export async function writeCsv(
  fileName: string,
  rows: Record<string, string>[],
  headers: string[]
) {
  const filePath = path.join(dataDir, fileName);
  await fs.writeFile(filePath, serializeCsv(rows, headers), "utf8");
}

export async function appendCsv(
  fileName: string,
  row: Record<string, string>,
  headers: string[]
) {
  const filePath = path.join(dataDir, fileName);
  const line = `${headers.map((header) => escapeCsv(row[header] ?? "")).join(",")}\n`;
  await fs.appendFile(filePath, line, "utf8");
}

function escapeCsv(value: string) {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replaceAll('"', '""')}"`;
  }
  return value;
}
