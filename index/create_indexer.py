from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient  
from azure.search.documents.indexes.models import (  
    SearchIndex, SimpleField, SearchFieldDataType, SearchIndexer, SearchIndexerDataSourceConnection,  
    SearchIndexerSkillset, CognitiveServicesAccountKey, InputFieldMappingEntry, OutputFieldMappingEntry,  
    EntityRecognitionSkill, KeyPhraseExtractionSkill, OcrSkill, SearchIndexerDataContainer,  
    SentimentSkill, LanguageDetectionSkill, PIIDetectionSkill  
)  
from azure.storage.blob import BlobServiceClient  
from azure.identity import DefaultAzureCredential  
from azure.core.credentials import AzureKeyCredential  
import os  
from dotenv import load_dotenv  
  
load_dotenv()  
  
search_service_endpoint = os.getenv("AZURE_SEARCH_SERVICE_ENDPOINT")  
search_api_key = os.getenv("AZURE_SEARCH_API_KEY")  
if not search_api_key:  
    raise ValueError("AZURE_SEARCH_API_KEY environment variable is not set.")  
  
credential = DefaultAzureCredential()  
blob_service_client = BlobServiceClient(account_url=os.getenv("AZURE_STORAGE_ACCOUNT_URL"), credential=credential)  
blob_connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")  
blob_container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME")  
  
# Create clients  
index_client = SearchIndexClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(search_api_key))  
indexer_client = SearchIndexerClient(endpoint=search_service_endpoint, credential=AzureKeyCredential(search_api_key))  
  
# Define the search index  
index_name = "rfp-index"  
fields = [  
    SimpleField(name="id", type=SearchFieldDataType.String, key=True),  
    SimpleField(name="content", type=SearchFieldDataType.String),  
    SimpleField(name="fileName", type=SearchFieldDataType.String),  
    SimpleField(name="uploadDate", type=SearchFieldDataType.String),  
    SimpleField(name="guid", type=SearchFieldDataType.String),  
    SimpleField(name="keyPhrases", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),  
    SimpleField(name="languageCode", type=SearchFieldDataType.String),  
    SimpleField(name="sentimentScore", type=SearchFieldDataType.Double),  
    SimpleField(name="persons", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),  
    SimpleField(name="organizations", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),  
    SimpleField(name="locations", type=SearchFieldDataType.Collection(SearchFieldDataType.String)),  
    SimpleField(name="metadata_storage_path", type=SearchFieldDataType.String),  
    SimpleField(name="metadata_storage_name", type=SearchFieldDataType.String),  
    SimpleField(name="metadata_storage_last_modified", type=SearchFieldDataType.DateTimeOffset),  
    SimpleField(name="metadata_storage_content_type", type=SearchFieldDataType.String),  
    SimpleField(name="metadata_storage_size", type=SearchFieldDataType.Int32),
]  
  
index = SearchIndex(name=index_name, fields=fields)  
index_client.create_index(index)  
  
# Define the data source  
data_source_name = "rfp-datasource"  
data_source = SearchIndexerDataSourceConnection(  
    name=data_source_name,  
    type="azureblob",  
    connection_string=blob_connection_string,  
    container=SearchIndexerDataContainer(name=blob_container_name)  
)  
indexer_client.create_data_source_connection(data_source)  
  
# Define the skillset  
skillset_name = "rfp-skillset"  
skills = [  
    OcrSkill(  
        name="ocr-skill",  
        description="Extract text from images",  
        context="/document",  
        inputs=[InputFieldMappingEntry(name="image", source="/document/content")],  
        outputs=[OutputFieldMappingEntry(name="text", target_name="text")]  
    ),  
    KeyPhraseExtractionSkill(  
        name="keyphrase-skill",  
        description="Extract key phrases",  
        context="/document",  
        inputs=[InputFieldMappingEntry(name="text", source="/document/text")],  
        outputs=[OutputFieldMappingEntry(name="keyPhrases", target_name="keyPhrases")]  
    ),  
    EntityRecognitionSkill(  
        name="entity-skill",  
        description="Extract entities",  
        context="/document",  
        inputs=[InputFieldMappingEntry(name="text", source="/document/text")],  
        outputs=[  
            OutputFieldMappingEntry(name="persons", target_name="persons"),  
            OutputFieldMappingEntry(name="organizations", target_name="organizations"),  
            OutputFieldMappingEntry(name="locations", target_name="locations"),  
            # Add more as needed  
        ]  
    ),  
    SentimentSkill(  
        name="sentiment-skill",  
        description="Analyze sentiment",  
        context="/document",  
        inputs=[InputFieldMappingEntry(name="text", source="/document/text")],  
        outputs=[OutputFieldMappingEntry(name="sentiment", target_name="sentimentScore")]  
    ),  
    LanguageDetectionSkill(  
        name="language-skill",  
        description="Detect language",  
        context="/document",  
        inputs=[InputFieldMappingEntry(name="text", source="/document/text")],  
        outputs=[OutputFieldMappingEntry(name="languageCode", target_name="languageCode")]  
    )      
]  
  
skillset = SearchIndexerSkillset(  
    name=skillset_name,  
    skills=skills,  
    cognitive_services_account=CognitiveServicesAccountKey(key=os.getenv("AZURE_COGNITIVE_SERVICES_KEY"))  
)  
indexer_client.create_skillset(skillset)  
  
# Define the indexer  
indexer_name = "rfp-indexer"  
indexer = SearchIndexer(  
    name=indexer_name,  
    data_source_name=data_source_name,  
    target_index_name=index_name,  
    skillset_name=skillset_name,  
    field_mappings=[  
        {"sourceFieldName": "metadata_storage_path", "targetFieldName": "id"},  
        {"sourceFieldName": "metadata_storage_name", "targetFieldName": "fileName"},  
        {"sourceFieldName": "metadata_storage_last_modified", "targetFieldName": "uploadDate"},  
        {"sourceFieldName": "metadata_storage_path", "targetFieldName": "guid"}  
    ],  
    output_field_mappings=[  
        {"sourceFieldName": "/document/text", "targetFieldName": "content"},  
        {"sourceFieldName": "/document/keyPhrases", "targetFieldName": "keyPhrases"},  
        {"sourceFieldName": "/document/languageCode", "targetFieldName": "languageCode"},  
        {"sourceFieldName": "/document/sentimentScore", "targetFieldName": "sentimentScore"},  
        {"sourceFieldName": "/document/persons", "targetFieldName": "persons"},  
        {"sourceFieldName": "/document/organizations", "targetFieldName": "organizations"},  
        {"sourceFieldName": "/document/locations", "targetFieldName": "locations"},  
    ]  
)  
indexer_client.create_indexer(indexer)  
  
print("Indexer pipeline setup complete.")  