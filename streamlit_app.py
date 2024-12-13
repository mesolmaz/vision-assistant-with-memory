import asyncio
import time
import json
import requests
import uuid
import base64
import streamlit as st
from langchain_core.messages import HumanMessage

st.title("Vision Assistant chat-bot")
url = "http://localhost:8000/invocations/"

async def async_response_generator(placeholder, prompt, encoded_image, config):

    input = {"prompt": prompt, "image": encoded_image, "config": config}
    payload = json.dumps(input)
    resp = requests.post(url, data=payload)
    resp.raise_for_status()
    if resp.status_code == 200:
        streamed_text = json.loads(resp.content.decode())["text"]
        placeholder.write(streamed_text)
        st.session_state.messages.append({"type": "assistant", "content": streamed_text})
    else:
        placeholder.write("Error: ", resp.status_code)

async def display_image(image_url):
    st.image(image_url, width=200)

async def main() -> None:
    if "thread_id" not in st.session_state:
        thread_id = st.query_params.get("thread_id")
        if not thread_id:
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}
            messages = []
        st.session_state.messages = messages
        st.session_state.thread_id = thread_id
        st.session_state.config = config

    # Display chat messages from history on app rerun
    for message in st.session_state.messages:
        with st.chat_message(message["type"]):
            if "image_url" in message:
                st.markdown(message["content"])
                await display_image(message["image_url"])
            else:
                st.markdown(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?", accept_file=True, file_type=["jpg"]):
        # print(prompt["text"])
        if prompt["files"]:
            encoded_image = base64.b64encode(prompt["files"][0].getvalue()).decode("utf-8")
            # Add user message to chat history
            st.session_state.messages.append({
            "type": "user", 
            "content": prompt["text"],
            "image_url": prompt["files"][0]})
        else:
            # Add user message to chat history
            st.session_state.messages.append({
            "type": "user", 
            "content": prompt["text"]})
            encoded_image = None

        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt["text"])
            if prompt["files"]:
                st.image(prompt["files"][0])

        ai_placeholder = st.chat_message("assistant")
        await async_response_generator(ai_placeholder, prompt["text"], encoded_image, st.session_state.config)

if __name__ == "__main__":
    asyncio.run(main())