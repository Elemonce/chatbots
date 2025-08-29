from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from dotenv import load_dotenv
import os


load_dotenv()


app = FastAPI()

# Allow frontend (JavaScript in browser) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

project = AIProjectClient(
    credential=DefaultAzureCredential(),
    endpoint=os.getenv("AI_D_PROJECT_ENDPOINT")
)

agent = project.agents.get_agent(os.getenv("AGENT_ID"))
# agent = os.getenv("AGENT_ID")
thread = project.agents.threads.create()

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data["message"]

    message = project.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input
    )

    run = project.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id
    )

    if run.status == "failed":
        return {"role": "assistant", "message": f"Run failed: {run.last_error}"}

    # messages = project.agents.messages.list(
    messages = list(project.agents.messages.list(
        thread_id=thread.id,
        order=ListSortOrder.ASCENDING
    ))

    # last assistant message
    for message in reversed(messages):
        if message.role == "assistant" and message.text_messages:
            return {"role": "assistant", "message": message.text_messages[-1].text.value}

    return {"role": "assistant", "message": "No response"}
