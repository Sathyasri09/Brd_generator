# BRD Generator using LLM

This project generates a **professional Business Requirements Document (BRD)** from a simple project description using an LLM.

## Features
- Validates user input
- Generates structured BRD with:
  - Functional Requirements
  - Non-Functional Requirements
  - Data Tables
  - Architecture
  - Acceptance Criteria

## Tech Stack
- Python
- LangGraph
- Chainlit (UI)
- LLM (Ollama / OpenAI / HF)

## How to Run

```bash
pip install -r requirements.txt
chainlit run app.py
