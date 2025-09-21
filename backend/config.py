# config.py
import os
import logging
from dotenv import load_dotenv
from agno.models.aws import AwsBedrock
from agno.storage.agent.mongodb import MongoDbAgentStorage
from agno.memory.v2.db.mongodb import MongoMemoryDb
from agno.memory.v2.memory import Memory
from agno.vectordb.qdrant import Qdrant
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.combined import CombinedKnowledgeBase
from agno.knowledge.pdf import PDFKnowledgeBase
from agno.knowledge.text import TextKnowledgeBase
from agno.knowledge.docx import DocxKnowledgeBase

load_dotenv()

# Logging Configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Application Configuration ---

# MongoDB configuration
MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "legal_agent_system")

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = "legal_knowledge_base"

# Embedding configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))

# Knowledge base directory
KNOWLEDGE_BASE_DIR = os.getenv("KNOWLEDGE_BASE_DIR", "./knowledge_base")

# AWS Bedrock model configuration
BASE_MODEL = AwsBedrock(
    id=os.getenv("AWS_BEDROCK_MODEL", "openai.gpt-oss-120b-1:0"),
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    aws_region=os.getenv("AWS_REGION", "us-west-2")
)

# Frontend URL for CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# --- Service Connections ---

# Qwen3 Embedder for vector operations
embedder = SentenceTransformerEmbedder(
    id=EMBEDDING_MODEL
)

# Qdrant Vector Database
vector_db = Qdrant(
    collection=QDRANT_COLLECTION,
    url=QDRANT_URL,
    embedder=embedder,
    distance="cosine"  
)

# Storage for agent session history
agent_storage = MongoDbAgentStorage(
    collection_name="agent_data",
    db_url=MONGO_URL,
    db_name=DATABASE_NAME
)

# Memory V2 MongoDB backend
memory_db = MongoMemoryDb(
    collection_name="agent_memories",
    db_url=MONGO_URL,
    db_name=DATABASE_NAME
)
memory = Memory(db=memory_db)

# --- Knowledge Base Configuration ---

# Legal Knowledge Base - combining multiple document types
legal_knowledge_base = CombinedKnowledgeBase(
    sources=[
        PDFKnowledgeBase(
            path=f"{KNOWLEDGE_BASE_DIR}/pdfs",
            vector_db=vector_db,
            reader_config={"chunk_size": 1500, "chunk_overlap": 200, "separator": "\n\n"},
        ),
        DocxKnowledgeBase(
            path=f"{KNOWLEDGE_BASE_DIR}/docx",
            vector_db=vector_db,
            reader_config={"chunk_size": 1500, "chunk_overlap": 200},
        ),
        TextKnowledgeBase(
            path=f"{KNOWLEDGE_BASE_DIR}/texts",
            vector_db=vector_db,
            reader_config={"chunk_size": 1500, "chunk_overlap": 200},
        ),
    ],

    vector_db=vector_db,
)
# Knowledge search configuration
KNOWLEDGE_SEARCH_CONFIG = {
    "num_documents": int(os.getenv("MAX_SEARCH_RESULTS", "5")),
    "similarity_threshold": float(os.getenv("SEARCH_SIMILARITY_THRESHOLD", "0.7"))
}
