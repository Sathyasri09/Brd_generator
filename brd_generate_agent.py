from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from google import genai
from docx import Document
from htmldocx import HtmlToDocx
import os
import re
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


class BRDState(TypedDict):
    project_name: str
    user_input: str
    headings: list
    brd_html: str
    output_path: str
    file_name: str
    final_docx: str
    is_valid: bool
    brd_template_file: str


def extract_headings_node(state: BRDState) -> BRDState:
    """Extract Heading 1 from the template"""
    doc = Document(state["brd_template_file"])
    headings = []
    for para in doc.paragraphs:
        if para.style.name == "Heading 1":
            clean = re.sub(r"\s*\(.*?\)\s*", "", para.text.strip())
            if clean:
                headings.append(clean)
    state["headings"] = headings
    print("Extracted Headings:", headings)
    return state

def validate_input_node(state: BRDState) -> BRDState:
    """Check if user input is valid"""
    state["is_valid"] = len(state["user_input"].split()) >= 5
    if not state["is_valid"]:
        print("Invalid input detected")
    return state

def generate_brd_html_node(state: BRDState) -> BRDState:
    """Generate HTML BRD using Google Gemini API"""
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise Exception("GOOGLE_API_KEY not set")

    client = genai.Client(api_key=GOOGLE_API_KEY)
    model = "gemini-3-flash-preview"

    prompt = f"""
You are an expert Business Analyst. Generate a professional BRD for the following project:

Project Description: {state['user_input']}

Use the following main headings: {', '.join(state['headings'])}.
Include numbered subheadings, bullet points, and tables where necessary.
Output HTML using <h1>, <h2>, <h3>, <p>, <ul>, <li>, <table>, <tr>, <th>, <td>.
Do not use markdown.
Tables must include headers.
"""
    response = client.models.generate_content(model=model, contents=prompt)
    state["brd_html"] = getattr(response, "text", None) or \
                        getattr(response, "output_text", None) or \
                        response.contents[0].text
    print("AI HTML Generated")
    return state

def html_to_word_node(state: BRDState) -> BRDState:
    """Convert HTML BRD to Word document"""
    if not state.get("brd_html"):
        print("ERROR: brd_html is empty!")
        return state

    os.makedirs("files", exist_ok=True)

    doc = Document()
    parser = HtmlToDocx()
    parser.add_html_to_document(state["brd_html"], doc)

    for table in doc.tables:
        table.style = "Table Grid"

    safe_proj_name = re.sub(r'[\\/*?:"<>|]', "_", state["project_name"])
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"BRD_{safe_proj_name}_{timestamp}.docx"
    output_path = os.path.join("files", file_name)

    doc.save(output_path)

    state["output_path"] = os.path.abspath(output_path)
    state["file_name"] = file_name
    state["final_docx"] = state["output_path"]
    print(f"Word document : {state['final_docx']}")
    return state

def invalid_output_node(state: BRDState) -> BRDState:
    print("Please provide a valid project description.")
    return state


builder = StateGraph(BRDState)
builder.add_node("extract_headings_node", extract_headings_node)
builder.add_node("validate_input_node", validate_input_node)
builder.add_node("generate_brd_html_node", generate_brd_html_node)
builder.add_node("html_to_word_node", html_to_word_node)
builder.add_node("invalid_output_node", invalid_output_node)

builder.add_edge(START, "extract_headings_node")
builder.add_edge("extract_headings_node", "validate_input_node")

def route_after_validation(state: BRDState):
    return "generate_brd_html_node" if state["is_valid"] else "invalid_output_node"

builder.add_conditional_edges("validate_input_node", route_after_validation)
builder.add_edge("generate_brd_html_node", "html_to_word_node")
builder.add_edge("html_to_word_node", END)
builder.add_edge("invalid_output_node", END)

graph = builder.compile()
