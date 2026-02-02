from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from google import genai
import os
import re
from docx import Document
from fpdf import FPDF
from dotenv import load_dotenv
import textwrap

load_dotenv()

# ---------------- STATE DEFINITION ----------------
class BRDState(TypedDict):
    project_name: str
    brd_text: str
    brd_sections: dict
    user_input: str
    brd_template_file: str
    is_valid: bool
    final_pdf: str

# ---------------- NODE 1 — INPUT ----------------
def input_node(state: BRDState) -> BRDState:
    print(f"📌 Project Input Received: {state['user_input']}")
    return state

# ---------------- HELPER: PARSE TEMPLATE ----------------
def parse_template_headings(template_file: str):
    doc = Document(template_file)
    headings = []
    for para in doc.paragraphs:
        if para.style.name.startswith("Heading"):
            headings.append(para.text.strip())
    return headings

# ---------------- NODE 2 — GENERATE BRD ----------------
def validate_and_generate_node(state: BRDState) -> BRDState:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not found")

    client = genai.Client(api_key=GOOGLE_API_KEY)
    model = "gemini-2.5-flash"

    project_name = state["project_name"]
    project_description = state["user_input"]
    template_file = state["brd_template_file"]

    if not template_file:
        raise ValueError("No BRD template file provided.")

    headings = parse_template_headings(template_file)

    # Combine all headings in one prompt
    prompt_headings = "\n".join([f"{i+1}. {h}" for i, h in enumerate(headings)])

    prompt = f"""
You are a professional Business Analyst.

Generate a complete BRD for the following project:

PROJECT NAME: {project_name}
PROJECT DESCRIPTION: {project_description}

Please generate detailed sections for all of these headings:
{prompt_headings}

Rules:
- Keep it professional.
- Keep sections concise but informative.
- Output plain text only, start each section with its heading as shown.
"""

    # Single API call
    response = client.models.generate_content(model=model, contents=prompt)
    brd_text = response.text.strip()

    # Optional: split into sections
    sections = {}
    current_heading = None
    for line in brd_text.split("\n"):
        line = line.strip()
        if any(line.startswith(f"{i+1}. {h}") for i, h in enumerate(headings)):
            current_heading = line
            sections[current_heading] = ""
        elif current_heading:
            sections[current_heading] += line + "\n"

    state["brd_sections"] = sections
    state["brd_text"] = brd_text
    state["is_valid"] = True
    print("✅ BRD Generated Successfully based on template!")
    return state

# ---------------- NODE 3 — PARSE SECTIONS ----------------
def split_sections_node(state: BRDState) -> BRDState:
    brd_lines = state["brd_text"].split("\n")
    sections = {}
    current_heading = None

    for line in brd_lines:
        line = line.strip()
        if re.match(r"^\d+(\.\d+)*\s", line):
            current_heading = line
            sections[current_heading] = ""
        elif current_heading:
            sections[current_heading] += line + "\n"

    state["brd_sections"] = sections
    print("📂 BRD split into sections successfully!")
    return state

# ---------------- PDF CREATION ----------------
def markdown_to_pdf(brd_text: str, output_pdf: str = "final_brd.pdf") -> str:
    pdf = FPDF(format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # Set proper margins
    left_margin = 15
    right_margin = 15
    pdf.set_left_margin(left_margin)
    pdf.set_right_margin(right_margin)

    pdf.add_page()

    page_width = pdf.w - left_margin - right_margin  # Safe writable width

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.cell(page_width, 10, "Business Requirements Document (BRD)", ln=True, align="C")
    pdf.ln(8)

    lines = brd_text.split("\n")

    for line in lines:
        line = line.strip()

        if not line:
            pdf.ln(3)
            continue

        # Section Headings (1. Introduction, 2. Scope, etc.)
        if re.match(r"^\d+(\.\d+)*\s", line):
            pdf.set_font("Arial", "B", 13)
            pdf.ln(2)
            pdf.multi_cell(page_width, 8, line)
            pdf.ln(1)

        # Normal Paragraph Text
        else:
            pdf.set_font("Arial", "", 11)

            # Prevent long unbroken text from breaking layout
            safe_line = line.encode("latin-1", "replace").decode("latin-1")

            pdf.multi_cell(page_width, 6, safe_line)
            pdf.ln(1)

    pdf.output(output_pdf)
    print(f"📕 Final PDF Ready: {output_pdf}")
    return output_pdf

# ---------------- NODE 4 — OUTPUT PDF ----------------
def output_node(state: BRDState) -> BRDState:
    pdf_path = "final_brd.pdf"
    markdown_to_pdf(state["brd_text"], pdf_path)
    state["final_pdf"] = pdf_path   # ⭐ THIS is what UI needs
    return state


# ---------------- GRAPH ----------------
builder = StateGraph(BRDState)
builder.add_node("input_node", input_node)
builder.add_node("validate_and_generate_node", validate_and_generate_node)
builder.add_node("split_sections_node", split_sections_node)
builder.add_node("output_node", output_node)

builder.add_edge(START, "input_node")
builder.add_edge("input_node", "validate_and_generate_node")

def route_after_validation(state: BRDState):
    return "split_sections_node" if state["is_valid"] else END

builder.add_conditional_edges(
    "validate_and_generate_node",
    route_after_validation,
    {"split_sections_node": "split_sections_node", END: END},
)

builder.add_edge("split_sections_node", "output_node")
builder.add_edge("output_node", END)

graph = builder.compile()
