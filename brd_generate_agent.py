from langgraph.graph import StateGraph, START, END
from typing import TypedDict
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()

class BRDState(TypedDict):
    project_name: str
    brd_text: str
    brd_sections: dict
    user_input: str
    is_valid: bool

def input_node(state: BRDState) -> BRDState:
    print(f"Project Input Received: {state['user_input']}")
    return state



def validate_and_generate_node(state: BRDState) -> BRDState:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    client = genai.Client(api_key=GOOGLE_API_KEY) 
    model = "gemini-3-flash-preview"

    prompt = f"""
You are an expert Business Analyst. Your task is to generate a professional, detailed Business Requirements Document (BRD) for a software/system project.

Step 1: Check if the following text is a valid project description suitable for generating a BRD.
- A valid description must clearly state the project purpose, goals, or system functionality.
- If valid, generate a Detailed and professional BRD in the following structure:

1. Document Control (with Version, Date, Author, Description table)
2. Introduction (Purpose, Scope, Objectives)
3. Functional Requirements (table: ID, Requirement, Detailed Explanation)
4. Non-Functional Requirements (table: Category, Requirement, Explanation)
5. System Architecture (describe high-level architecture)
6. Interfaces (table: Type, Interface, Details)
7. Data Requirements (table: Entity, Attributes, Explanation)
8. Assumptions
9. Acceptance Criteria (table: ID, Description)
10. Appendices / Glossary

Additional instructions:
- Include **tables where appropriate**.
- Provide **detailed explanation for each functional/non-functional requirement**.
- Use **numbered headings** for sections and subsections.
- Write in a **professional, client-ready format**, suitable for Word or PDF.

Project Description:
{state['user_input']}

Step 2: If input is invalid, reply ONLY with:
INVALID INPUT
"""


    response = client.models.generate_content(
        model=model,
        contents=prompt
    )

    output_text = response.text.strip()

    if "INVALID INPUT" in output_text.upper():
        state["brd_text"] = (
            "Invalid project description.\n\n"
            "Please describe a software/system project with details like features, users, or purpose."
        )
        state["is_valid"] = False
    else:
        state["brd_text"] = output_text
        state["is_valid"] = True
        print("BRD Generated Successfully!")

    return state

def split_sections_node(state: BRDState) -> BRDState:
    brd_lines = state["brd_text"].split("\n")
    sections = {}
    current_section = None

    for line in brd_lines:
        line = line.strip()
        if line.endswith(":") and len(line.split()) <= 5:
            current_section = line[:-1]
            sections[current_section] = ""
        elif current_section:
            sections[current_section] += line + "\n"

    state["brd_sections"] = sections
    print("BRD split into sections successfully!")
    return state

def output_node(state: BRDState) -> BRDState:
    return state

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
