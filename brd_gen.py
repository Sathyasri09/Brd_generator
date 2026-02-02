import chainlit as cl
from brd_generate_agent import graph

@cl.on_chat_start
async def start():
    await cl.Message(
        content="📄 Upload a BRD template (.docx) and describe your project."
    ).send()


@cl.on_message
async def main(message: cl.Message):
    user_description = message.content or ""
    template_file_path = None

    # Get uploaded template
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

    # Show generating message AND keep reference
    generating_msg = await cl.Message(
        content="⏳ Generating your BRD... please wait..."
    ).send()

    # Run agent
    result = graph.invoke({
        "project_name": "User Project",
        "user_input": user_description,
        "brd_template_file": template_file_path,
        "brd_text": "",
        "brd_sections": {},
        "is_valid": False,
        "final_pdf": ""
    })

    pdf_path = result["final_pdf"]

    # Send PDF attached to the generating message
    file = cl.File(
        name="BRD_Document.pdf",
        path=pdf_path
    )

    await file.send(for_id=generating_msg.id)

    await cl.Message(content="✅ Your BRD PDF is ready!").send()
