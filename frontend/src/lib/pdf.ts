import { getDocument, GlobalWorkerOptions } from "pdfjs-dist";
import workerSrc from "pdfjs-dist/build/pdf.worker.min.mjs?url";

// pdf.js needs its worker; Vite resolves the asset URL at build time.
GlobalWorkerOptions.workerSrc = workerSrc;

export interface ExtractedResume {
  text: string;
  pageCount: number;
}

// Extract all text from a PDF file. Returns normalized whitespace so the
// screening skill-matcher sees clean tokens ("Go, PostgreSQL, Kubernetes").
export async function extractTextFromPdf(file: File): Promise<ExtractedResume> {
  const data = new Uint8Array(await file.arrayBuffer());
  const loadingTask = getDocument({ data });
  try {
    const pdf = await loadingTask.promise;
    const parts: string[] = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const content = await page.getTextContent();
      const text = content.items
        .map((item) => ("str" in item ? item.str : ""))
        .join(" ");
      parts.push(text);
    }
    return { text: parts.join("\n").replace(/\s+/g, " ").trim(), pageCount: pdf.numPages };
  } finally {
    await loadingTask.destroy();
  }
}

export function readPdfName(name: string): string {
  return name.replace(/\.pdf$/i, "");
}
