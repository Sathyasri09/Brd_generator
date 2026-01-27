import chainlit as cl
from brd_generate_agent import graph


def extract_text(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"File read error: {e}")
        return ""



@cl.on_chat_start
async def start():
    await cl.Message(
        content="Hi! Either type your project details OR upload a .txt file."
    ).send()



    
@cl.on_message
async def main(message: cl.Message):
    user_input = ""

 
    if message.elements:
        for element in message.elements:
            if element.path:
                user_input = extract_text(element.path)
                break

    
    if not user_input:
        user_input = message.content or ""

   
    if not user_input.strip():
        await cl.Message(content="Please type details or upload a .txt file.").send()
        return

      

    await cl.Message(content="Generating BRD... please wait...").send()

 
    result = graph.invoke({
        "project_name": "User Project",
        "user_input": user_input,
        "brd_text": "",
        "brd_sections": {},
        "is_valid": False  
    })

    brd_output = result.get("brd_text", "No BRD generated.")


    await cl.Message(content=brd_output).send()
