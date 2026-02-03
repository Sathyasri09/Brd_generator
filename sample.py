import chainlit as cl
from brd_generate_agent import graph  # Your Word-based BRD graph

@cl.on_chat_start
async def start():
    await cl.Message(
        content="📄 Upload a BRD template (.docx) and describe your project."
    ).send()

@cl.on_message
async def main(message: cl.Message):
    user_description = message.content or ""
    template_file_path = None

    # Get uploaded template file
    if message.elements:
        for element in message.elements:
            if element.path and element.path.endswith(".docx"):
                template_file_path = element.path
                break

    if not user_description.strip() or not template_file_path:
        await cl.Message(
            content="❌ Please upload a BRD template (.docx) AND provide a project description."
        ).send()
        return

    # Show "generating" message
    generating_msg = await cl.Message(
        content="⏳ Generating your BRD Word document... please wait..."
    ).send()

    # Run the graph in a separate thread (blocking operation)
    import asyncio
    import logging

    result = await asyncio.to_thread(
        graph.invoke,
        {
            "project_name": "User Project",
            "user_input": user_description,
            "brd_template_file": template_file_path,
            "headings": [],
            "brd_html": "",
            "output_path": "",
            "file_name": "",
            "final_docx": "",
            "is_valid": False
        }
    )

    logging.warning(f"GRAPH RESULT: {result}")  # Debugging in terminal

    docx_path = result.get("final_docx")

    if not docx_path:
        await cl.Message(content="❌ Failed to generate the BRD document.").send()
        return

    # Send the generated Word document to UI
    file = cl.File(
        name="BRD_Document.docx",
        path=docx_path
    )

    await file.send(for_id=generating_msg.id)
    await cl.Message(content="✅ Your BRD Word document is ready!").send()
