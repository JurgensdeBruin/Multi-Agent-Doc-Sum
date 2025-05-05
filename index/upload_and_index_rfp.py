import os
import uuid
import asyncio
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, HTTPException
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

import time

app = FastAPI()

# Azure Blob Storage configuration
credential = DefaultAzureCredential()
blob_service_client = BlobServiceClient(account_url=os.getenv("AZURE_STORAGE_ACCOUNT_URL"), credential=credential)

container_name = "rfp-documents"

# Azure AI Search configuration
search_service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")
search_index_name = "rfp-index"
search_client = SearchClient(endpoint=search_service_endpoint, index_name=search_index_name, credential=DefaultAzureCredential())
index_client = SearchIndexClient(endpoint=search_service_endpoint, credential=DefaultAzureCredential())
indexer_client = SearchIndexerClient(endpoint=search_service_endpoint, credential=DefaultAzureCredential())

# Azure AI Project configuration
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.getenv("PROJECT_CONNECTION_STRING")
)
rfp_analyzer_agent_id = os.getenv("RFP_ANALYZER_AGENT_ID")

@app.post("/upload-rfp")
async def upload_rfp(file: UploadFile = File(...)):
    try:
        # Generate a unique GUID for the document
        guid = str(uuid.uuid4())

        # Upload the document to Azure Blob Storage using GUID as the file name
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=guid)
        contents = await file.read()
        await blob_client.upload_blob(contents)


        # Trigger the indexer manually
        indexer_client.run_indexer("rfp-indexer")  # Replace with your actual indexer name

        # Poll the index for the new document using its GUID
        for _ in range(12):  # Poll for up to 60 seconds (12 * 5 seconds)
            try:
                document = search_client.get_document(guid)
                if document:
                    break
            except Exception:
                await asyncio.sleep(5)
        else:
            raise HTTPException(status_code=500, detail="Document indexing timed out")

        # Create a thread for the agent
        thread = project_client.agents.create_thread()

        # Create a message that includes the GUID to focus the agent's retrieval
        message = project_client.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=(
                f"Please analyze the RFP document with GUID: {guid}. "
                "Provide a summary, key requirements, keywords, and any compliance concerns."
            )
        )

        # Run the agent
        run = project_client.agents.create_and_process_run(
            thread_id=thread.id,
            agent_id=rfp_analyzer_agent_id
        )

        # Optional: Check run status and retrieve results
        if run.status == "completed":
            messages = project_client.agents.list_messages(thread_id=thread.id)
            for msg in messages:
                print(msg.text.value)

        return {"message": "Document uploaded, indexed, and analyzed successfully", "guid": guid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

