"""Generate proper one-page CV PDFs for every person in the synthetic corpus.

Reads canonical people/*.json (contact, summary, skills, experience, education,
certifications) and renders a clean single-page CV per person with fpdf2.

Usage:
    <venv>/bin/python scripts/synthetic/convert/generate_resume_pdfs.py

Writes: data/synthetic/out/resumes/<person-id>.pdf
        frontend/public/resumes/<person-id>.pdf   (served at /resumes/<file>)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parents[3] / "data" / "synthetic"
PEOPLE_DIR = ROOT / "people"
OUT_DIR = ROOT / "out" / "resumes"
PUBLIC_DIR = ROOT.parent.parent / "frontend" / "public" / "resumes"

# Unicode font so accented names and em/en dashes render correctly.
FONT_PATH = "/Library/Fonts/Arial Unicode.ttf"

# Paper / layout constants.
PAGE_W = 210
PAGE_H = 297
MARGIN = 14
CONTENT_W = PAGE_W - 2 * MARGIN

BRAND = (37, 99, 235)  # blue
DARK = (30, 41, 59)
GRAY = (107, 114, 128)
LIGHT = (243, 244, 246)


def safe(s: str | None) -> str:
    return s or "—"


def render(person: dict) -> FPDF:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_auto_page_break(auto=False)
    pdf.add_font("ArialUni", "", FONT_PATH)
    pdf.add_page()

    # -- Header band ---------------------------------------------------------
    pdf.set_fill_color(*BRAND)
    pdf.rect(0, 0, PAGE_W, 26, "F")

    pdf.set_font("ArialUni", "", 20)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(MARGIN, 6)
    pdf.cell(CONTENT_W, 8, safe(person["name"]))

    pdf.set_font("ArialUni", "", 11)
    pdf.set_xy(MARGIN, 15)
    pdf.cell(CONTENT_W, 5, safe(person["currentTitle"]))

    contact = [person["email"], person["phone"], person["location"]]
    pdf.set_font("ArialUni", "", 8)
    pdf.set_xy(MARGIN, 21)
    pdf.cell(CONTENT_W, 4, "  |  ".join(contact))

    y = 32

    def section(title: str) -> None:
        nonlocal y
        pdf.set_font("ArialUni", "", 9)
        pdf.set_text_color(*BRAND)
        pdf.set_xy(MARGIN, y)
        pdf.cell(CONTENT_W, 5, title.upper())
        pdf.set_draw_color(*BRAND)
        pdf.set_line_width(0.5)
        pdf.line(MARGIN, y + 5.5, PAGE_W - MARGIN, y + 5.5)
        y += 10

    def body(text: str, h: float = 4.5) -> None:
        nonlocal y
        pdf.set_font("ArialUni", "", 9)
        pdf.set_text_color(*DARK)
        pdf.set_xy(MARGIN, y)
        pdf.multi_cell(CONTENT_W, h, text, align="L")
        y = pdf.get_y() + 2

    # -- Summary -------------------------------------------------------------
    section("Professional Summary")
    body(person.get("summary") or person.get("resumeText", ""))

    # -- Skills --------------------------------------------------------------
    section("Core Skills")
    pdf.set_font("ArialUni", "", 9)
    pdf.set_text_color(*DARK)
    chunk = 4
    for i in range(0, len(person["skills"]), chunk):
        group = person["skills"][i : i + chunk]
        text = "   •   ".join(group)
        pdf.set_xy(MARGIN, y)
        pdf.cell(CONTENT_W, 5, text)
        y += 6

    # -- Experience ----------------------------------------------------------
    section("Professional Experience")
    for e in person["experience"]:
        if y > PAGE_H - 45:
            pdf.add_page()
            y = 14
        title = f"{e['title']}  ·  {e['company']}"
        end = "Present" if e.get("to") is None else e["to"]
        period = f"{e['from']} — {end}"
        pdf.set_font("ArialUni", "", 9.5)
        pdf.set_text_color(*DARK)
        pdf.set_xy(MARGIN, y)
        pdf.cell(CONTENT_W, 5, title)
        pdf.set_font("ArialUni", "", 8)
        pdf.set_text_color(*GRAY)
        pdf.set_xy(MARGIN, y + 5)
        pdf.cell(CONTENT_W, 4, period)
        y += 12

    # -- Education & Certifications ------------------------------------------
    if y > PAGE_H - 45:
        pdf.add_page()
        y = 14
    section("Education")
    body(person.get("education", "—"))
    section("Certifications")
    body(person.get("certifications", "—"))

    return pdf


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

    people = sorted(PEOPLE_DIR.glob("*.json"))
    for f in people:
        person = json.loads(f.read_text())
        pdf = render(person)
        stem = f.stem
        pdf.output(str(OUT_DIR / f"{stem}.pdf"))
        pdf.output(str(PUBLIC_DIR / f"{stem}.pdf"))

    print(f"Wrote {len(people)} CV PDFs -> {OUT_DIR} and {PUBLIC_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
