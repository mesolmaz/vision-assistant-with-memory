import json
import uvicorn
from typing import AsyncGenerator
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, trim_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, END, MessagesState, StateGraph
from langchain_openai import ChatOpenAI

model = ChatOpenAI(model="gpt-4o-mini", temperature=0,\
                   max_tokens=None, timeout=None)

app = FastAPI()

async def get_message(prompt, encoded) -> list[BaseMessage]:
    if encoded:
        return [
            HumanMessage(
            content=[
                {"type":"text", "text": prompt},
                {"type": "image_url", 
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encoded}"
                }
                }
            ]
        )]
    else:
        return [
            HumanMessage(
            content=[
                {"type":"text", "text": prompt}
            ]
        )]

async def call_model(state: MessagesState):
    system_prompt = (
        "You are an assistant that is good at identifying objects in images."
        "Answer all questions to the best of your ability."
    )
    state["messages"] = [SystemMessage(content=system_prompt)] + state["messages"]

    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}

# Define a new graph
workflow = StateGraph(state_schema=MessagesState)
# Define the two nodes we will cycle between
workflow.add_edge(START, "model")
workflow.add_node("model", call_model)
chatbot = workflow.compile(
    checkpointer=MemorySaver()
)

@app.get('/ping')
async def ping():
    return {"message": "ok"}

@app.get("/health")
async def health() -> Response:
    """Health check."""
    return Response(status_code=200)

@app.post("/invocations")
async def generate(request: Request) -> Response:

    request_dict = await request.json()
    prompt = request_dict.pop("prompt")
    image = request_dict.pop("image")
    config = request_dict.pop("config")
    # multimodal_prompt = asyncio.to_thread(get_message(prompt, image))
    multimodal_prompt = await get_message(prompt, image)
    async def stream_results() -> AsyncGenerator[bytes, None]:
        streamed_text = ""
        async for chunk in chatbot.astream({"messages": multimodal_prompt}, config=config):
            streamed_text = streamed_text + chunk["model"]["messages"][-1].content
            ret = {"text": streamed_text}
            yield (json.dumps(ret)).encode("utf-8")

    return StreamingResponse(stream_results())

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)