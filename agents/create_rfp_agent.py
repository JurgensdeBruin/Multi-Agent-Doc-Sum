import os
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import AzureAISearchTool
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient, BlobClient

# Connect to your Azure AI Foundry project
project_client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["PROJECT_CONNECTION_STRING"]
)

with project_client:
    # Define the Azure AI Search tool
    search_tool = AzureAISearchTool(
        index_name="rfp-index",
        search_endpoint=os.environ["AZURE_SEARCH_SERVICE_ENDPOINT"],
        embedding_dependency="azureopenai",
        fields_mapping={
            "content": "content",
            "title": "fileName",
            "filepath": "guid"
        }
    )

    # Agent 1 : RFP Analyzer Agent
    # This agent will analyze RFP documents and provide insights based on the content retrieved from Azure AI Search
    agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="rfp-analyzer-agent",
        instructions=(
            "You are a proposal assistant. Your job is to analyze RFP documents and provide:\n"
            "1. A concise summary of the RFP\n"
            "2. A list of key requirements and evaluation criteria\n"
            "3. Important keywords and themes\n"
            "4. Any potential compliance concerns\n"
            "Use the retrieved content from the RFP to ground your responses. Be clear, structured, and professional."
        ),
        tools=search_tool.definitions,
        tool_resources=search_tool.resources
    )

    print(f"Agent created successfully. Agent ID: {agent.id}")
    
    # Agent 2: RFP Question Answering Agent
    questionagent = project_client.agents.create_agent(
        model="gpt-4o",
        name="rfp-question-agent",
        instructions=(
            "You are an RFP assistant. Your job is to answer questions about the RFP documents. "
            "Use the retrieved content from the RFP to provide accurate and detailed responses. "
            "Be clear, structured, and professional."),
            tools=search_tool.definitions,
            tool_resources=search_tool.resources
            )
    print(f"Question Agent created successfully. Agent ID: {question_agent.id}")

    # Agent 3: RFP Proposal Writing Agent
    proposal_agent = project_client.agents.create_agent(
        model="gpt-4o",
        name="rfp-proposal-agent",
        instructions=(
            "You are a proposal writer. Your job is to generate a final RFP proposal based on the indexed content and user instructions. "
            "Use the retrieved content from the RFP to draft a comprehensive and tailored proposal. "
            "Ensure the proposal aligns with the requirements and evaluation criteria specified in the RFP. "
            "Be clear, structured, and professional."
            ),
            tools=search_tool.definitions,
            tool_resources=search_tool.resources)
    print(f"Proposal Agent created successfully. Agent ID: {proposal_agent.id}")

    