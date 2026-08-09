import io
import json

from docx import Document
from pypdf import PdfReader

from app.services.llm_client import chat_completion

STRUCTURING_PROMPT = """You are a resume parser. Extract structured data from the resume text below \
and return ONLY valid JSON (no markdown fences, no commentary) with this exact shape:

{{
  "name": string or null,
  "email": string or null,
  "phone": string or null,
  "summary": string or null,
  "skills": [string],
  "experience": [{{"company": string, "title": string, "start": string, "end": string, "highlights": [string]}}],
  "education": [{{"institution": string, "degree": string, "year": string}}]
}}

If a field is missing from the resume, use null or an empty list/array as appropriate. Do not invent data.

Resume text:
---
{resume_text}
---
"""


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if lower.endswith(".docx"):
        document = Document(io.BytesIO(file_bytes))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)
    raise ValueError(f"Unsupported resume file type: {filename} (only .pdf and .docx are supported)")


async def parse_resume(resume_text: str) -> dict:
    prompt = STRUCTURING_PROMPT.format(resume_text=resume_text[:12000])
    raw = await chat_completion([{"role": "user", "content": prompt}])

    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"raw_llm_output": raw, "parse_error": "model did not return valid JSON"}
