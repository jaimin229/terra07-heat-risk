"""Converts reports/report.md to reports/report.pdf using fpdf2 with robust encoding sanitization."""

from pathlib import Path
from fpdf import FPDF

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORT_MD = PROJECT_ROOT / "reports" / "report.md"
REPORT_PDF = PROJECT_ROOT / "reports" / "report.pdf"


def sanitize_text(text: str) -> str:
    replacements = {
        "₹": "INR ",
        "°": " deg ",
        "–": "-",
        "—": " - ",
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "≥": ">=",
        "≤": "<=",
        "≈": "~",
        "Δ": "Delta ",
        "β": "beta ",
        "ρ": "rho ",
        "ϵ": "epsilon ",
        "×": "x",
        "·": "*",
        "**": "",
        "`": "",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", "replace").decode("latin-1")


class PDFReport(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(100, 116, 139)
        self.cell(0, 8, "HeatLens - Team TERRA07 - Agnitia Hackathon 2026", align="L")
        self.cell(0, 8, "Page " + str(self.page_no()), align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, 16, 200, 16)
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(148, 163, 184)
        self.cell(0, 10, "Software Track: Heat-Risk Mapping at Human Scale - Ahmedabad Study Area", align="C")


def build_pdf():
    pdf = PDFReport()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    if not REPORT_MD.is_file():
        raise FileNotFoundError(f"{REPORT_MD} not found")

    lines = REPORT_MD.read_text(encoding="utf-8").split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            pdf.ln(2)
            continue

        clean_line = sanitize_text(stripped)

        if stripped.startswith("# "):
            pdf.set_font("Helvetica", "B", 15)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(pdf.epw, 7.5, clean_line[2:])
            pdf.ln(2)
        elif stripped.startswith("## "):
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(30, 58, 138)
            pdf.multi_cell(pdf.epw, 6.5, clean_line[3:])
            pdf.ln(1)
        elif stripped.startswith("### "):
            pdf.set_font("Helvetica", "B", 10.5)
            pdf.set_text_color(15, 23, 42)
            pdf.multi_cell(pdf.epw, 5.5, clean_line[4:])
            pdf.ln(1)
        elif stripped.startswith("+---") or stripped.startswith("|"):
            pdf.set_font("Courier", "", 7.5)
            pdf.set_text_color(51, 65, 85)
            pdf.cell(pdf.epw, 4.0, clean_line[:100], new_x="LMARGIN", new_y="NEXT")
        elif stripped.startswith("!["):
            img_path = PROJECT_ROOT / "reports" / "figures" / "architecture.png"
            if img_path.is_file():
                pdf.ln(2)
                pdf.image(str(img_path), w=180)
                pdf.ln(2)
        elif stripped.startswith("> "):
            pdf.set_font("Helvetica", "I", 9.0)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(pdf.epw, 4.5, clean_line[2:])
            pdf.ln(1)
        else:
            pdf.set_font("Helvetica", "", 9.0)
            pdf.set_text_color(30, 41, 59)
            pdf.multi_cell(pdf.epw, 4.5, clean_line)

    pdf.output(str(REPORT_PDF))
    print(f"Generated PDF short report at {REPORT_PDF}")


if __name__ == "__main__":
    build_pdf()
