from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import os
from supabase import create_client, Client

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


app = FastAPI()

# Allow frontend (JavaScript in browser) to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

credential=DefaultAzureCredential()

project = AIProjectClient(
    credential=credential,
    endpoint=os.getenv("AI_D_PROJECT_ENDPOINT")
)

# For testing purposes
# token = credential.get_token("https://management.azure.com/.default")
# print("Token acquired from:", credential.__class__.__name__)
# print("Access token (truncated):", token.token[:50] + "...")


agent = project.agents.get_agent(os.getenv("AGENT_ID"))
# thread = project.agents.threads.create()

@app.get("/health")
async def root():
    return {"status": "ok"}

@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def home():
    return "<h1>AI-D Chatbot API is running! </h1><p>Use POST /chat to talk to the bot.</p>"

@app.get("/chat", response_class=HTMLResponse)
def home():
    return "<h1>AI-D Chatbot API is running! </h1><p>Use POST /chat to talk to the bot.</p>"

@app.post("/start")
def give_thread_id():
    # Creating a thread for a new user
    thread = project.agents.threads.create()

    # Initial message to get initial response from the chatbot
    message = project.agents.messages.create(
        thread_id=thread.id,
        role="user",
        content="Hallo"
    )

    run = project.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent.id
    )

    if run.status == "failed":
        return {"role": "assistant", "message": f"Run failed: {run.last_error}"}
    
    messages = list(project.agents.messages.list(
    thread_id=thread.id,
    order=ListSortOrder.ASCENDING
    ))

    for message in reversed(messages):
        if message.role == "assistant" and message.text_messages:
            response = (
                supabase.table("chatbot_data")
                .insert({"role": "assistant", "message": message.text_messages[-1].text.value, "thread_id": thread.id})
                .execute()
            )
            print(response)        
            return {"role": "assistant", "message": message.text_messages[-1].text.value, "thread_id": thread.id}

    return {"role": "assistant", "message": "No response", "thread_id": thread.id}

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data["message"]
    user_thread_id = data["thread_id"]

    message = project.agents.messages.create(
        thread_id=user_thread_id,
        role="user",
        content=user_input
    )

    response_user = (
        supabase.table("chatbot_data")
        .insert({"role": "user", "message": user_input, "thread_id": user_thread_id})
        .execute()
    )

    run = project.agents.runs.create_and_process(
        thread_id=user_thread_id,
        agent_id=agent.id
    )

    if run.status == "failed":
        return {"role": "assistant", "message": f"Run failed: {run.last_error}"}

    # Getting a list of messages
    messages = list(project.agents.messages.list(
        thread_id=user_thread_id,
        order=ListSortOrder.ASCENDING
    ))

    # Last assistant message
    for message in reversed(messages):
        if message.role == "assistant" and message.text_messages:
            # [-1] here to get the last fragment in case one assistant message contains multiple text fragments
            response_assistant = (
                supabase.table("chatbot_data")
                .insert({"role": "assistant", "message": message.text_messages[-1].text.value, "thread_id": user_thread_id})
                .execute()
            )
            print(response_assistant)        

            return {"role": "assistant", "message": message.text_messages[-1].text.value}

    return {"role": "assistant", "message": "No response"}


# email, phone, name, summary (chatgpt)

# individual history
# storing the messages
# supabase (to store the messages maybe) WXyT79wgf9s4R6w3
# layout fix (logo etc)


# further steps
# cal.com api to make a meeting 