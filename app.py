from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
import os
import time

app = FastAPI()

# Azure AI Project configuration
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.getenv("PROJECT_CONNECTION_STRING")
)
question_agent_id = os.getenv("RFP_QUESTION_AGENT_ID")
proposal_agent_id = os.getenv("RFP_PROPOSAL_AGENT_ID")

class QuestionRequest(BaseModel):
    guid: str
    question: str

class ProposalRequest(BaseModel):
    guid: str
    instructions: str = None


@app.post("/ask-rfp-question")
async def ask_rfp_question(request: QuestionRequest):
    try:
        # Create a thread for the agent
        thread = project_client.agents.create_thread()
        # Add the user's question as a message
        project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=f"RFP GUID: {request.guid}\n\n{request.question}")
        
        # Create and start the run
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=question_agent_id)

        # Poll the run status until it's completed
        for _ in range(12):# Poll for up to 60 seconds
            run_status = project_client.agents.get_run(thread_id=thread.id, run_id=run.id)
            if run_status.status == "completed":
                break
            elif run_status.status in ["failed", "cancelled"]:
                raise HTTPException(status_code=500, detail=f"Run failed with status: {run_status.status}")
            time.sleep(5)

        # Retrieve the assistant's response
        messages = project_client.agents.list_messages(thread_id=thread.id)
        last_message = messages.get_last_text_message_by_role("assistant")
        if not last_message:    
            raise HTTPException(status_code=500, detail="No assistant response found.")
        return {"response": last_message.text.value}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/generate-rfp-proposal")
async def generate_rfp_proposal(request: ProposalRequest):
    try:
        # Create a thread for the agent
        thread = project_client.agents.create_thread()
        prompt = f"RFP GUID: {request.guid}\n\nPlease generate a proposal."
        if request.instructions:
            prompt += f"\n\nAdditional instructions: {request.instructions}"
        project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=prompt
        )
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=proposal_agent_id
        )
        messages = project_client.agents.list_messages(thread_id=thread.id)
        proposal = messages.get_last_text_message_by_role("assistant").text.value
        return {"proposal": proposal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agent-status/{thread_id}")
async def agent_status(thread_id: str):
    try:
        messages = project_client.agents.list_messages(thread_id=thread_id)
        last_message = messages.get_last_text_message_by_role("assistant")
        status = "completed" if last_message else "running"
        return {
            "status": status,
            "last_message": last_message.text.value if last_message else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

