# seed_qdrant.py
"""
Seed Qdrant Vector Database for the Legal Multi-Agent System:
- Creates collection with proper configuration
- Loads legal documents (PDF, DOCX, TXT) into vector database
- Links with MongoDB through document metadata
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv

# Qdrant and embedding imports
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, CreateCollection,
    PointStruct, Record
)

# Agno imports for document processing
# ADD THIS LINE
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.pdf import PDFReader
from agno.knowledge.docx import DocxReader
from agno.knowledge.text import TextReader

# MongoDB for cross-referencing
import pymongo

def create_knowledge_base_directories():
    """Create knowledge base directory structure if it doesn't exist."""
    base_dir = Path("./knowledge_base")
    subdirs = ["pdfs", "docx", "texts"]
    
    for subdir in subdirs:
        (base_dir / subdir).mkdir(parents=True, exist_ok=True)
    
    return base_dir

def create_sample_documents(base_dir: Path):
    """Create sample legal documents for testing."""
    
    # Sample legal texts
    sample_texts = {
        "contract_law_basics.txt": """
Contract Law Fundamentals

1. ESSENTIAL ELEMENTS OF A CONTRACT

For a contract to be legally binding, it must contain the following essential elements:

a) Offer: A clear proposal made by one party (offeror) to another party (offeree)
b) Acceptance: Unqualified agreement to the terms of the offer
c) Consideration: Something of value exchanged between the parties
d) Intention to create legal relations: Both parties must intend for the agreement to be legally binding
e) Capacity: Both parties must have the legal capacity to enter into the contract
f) Legality: The contract's purpose and terms must be legal

2. TYPES OF CONTRACTS

- Express Contracts: Terms are explicitly stated (written or oral)
- Implied Contracts: Terms are inferred from conduct or circumstances
- Bilateral Contracts: Both parties make promises
- Unilateral Contracts: One party makes a promise in exchange for performance

3. CONTRACT PERFORMANCE AND BREACH

Performance can be:
- Complete Performance: All obligations fulfilled
- Substantial Performance: Performance with minor deviations
- Material Breach: Significant failure to perform

Document ID: CONTRACT_LAW_001
Jurisdiction: General Common Law Principles
Last Updated: 2024-01-15
""",

        "gdpr_compliance.txt": """
General Data Protection Regulation (GDPR) Compliance Guide

1. FUNDAMENTAL PRINCIPLES

Article 5 establishes six key principles for data processing:
a) Lawfulness, fairness, and transparency
b) Purpose limitation
c) Data minimization
d) Accuracy
e) Storage limitation
f) Integrity and confidentiality

2. LAWFUL BASIS FOR PROCESSING (Article 6)

- Consent of the data subject
- Performance of a contract
- Compliance with legal obligation
- Protection of vital interests
- Performance of a task in the public interest
- Legitimate interests of the controller

3. DATA SUBJECT RIGHTS

- Right to information (Articles 13-14)
- Right of access (Article 15)
- Right to rectification (Article 16)
- Right to erasure (Article 17)
- Right to restrict processing (Article 18)
- Right to data portability (Article 20)
- Right to object (Article 21)

4. COMPLIANCE REQUIREMENTS FOR ORGANIZATIONS

- Data Protection Officer (DPO) appointment when required
- Privacy by Design and Default
- Data Protection Impact Assessment (DPIA)
- Records of processing activities
- Breach notification procedures

Document ID: GDPR_COMPLIANCE_001
Jurisdiction: European Union
Regulation: EU 2016/679
Last Updated: 2024-01-15
""",

        "intellectual_property_overview.txt": """
Intellectual Property Law Overview

1. TYPES OF INTELLECTUAL PROPERTY

a) PATENTS
- Protect inventions and innovations
- Duration: 20 years from filing date
- Requirements: Novel, non-obvious, useful

b) TRADEMARKS
- Protect brand names, logos, slogans
- Duration: Renewable indefinitely
- Requirements: Distinctive, used in commerce

c) COPYRIGHTS
- Protect original works of authorship
- Duration: Life of author + 70 years (generally)
- Requirements: Original, fixed in tangible medium

d) TRADE SECRETS
- Protect confidential business information
- Duration: As long as kept secret
- Requirements: Economic value, reasonable secrecy measures

2. PATENT PROSECUTION PROCESS

- Prior art search
- Patent application drafting
- USPTO examination
- Office action responses
- Patent grant or abandonment

3. TRADEMARK REGISTRATION

- Trademark search
- Application filing
- Examination by USPTO
- Publication for opposition
- Registration

4. COPYRIGHT PROTECTION

- Automatic upon creation
- Registration provides additional benefits
- Fair use doctrine limitations
- DMCA safe harbor provisions

Document ID: IP_OVERVIEW_001
Jurisdiction: United States
Last Updated: 2024-01-15
"""
    }
    
    # Create sample text files
    texts_dir = base_dir / "texts"
    for filename, content in sample_texts.items():
        (texts_dir / filename).write_text(content, encoding='utf-8')
    
    print(f"Created {len(sample_texts)} sample legal documents in {texts_dir}")

def seed_qdrant_database():
    """Main function to seed Qdrant with legal documents."""
    load_dotenv()
    
    # Configuration
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_COLLECTION = "legal_knowledge_base"
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
    EMBEDDING_DIMENSIONS = int(os.getenv("EMBEDDING_DIMENSIONS", "1024"))
    
    # MongoDB configuration for cross-referencing
    MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "legal_agent_system")
    
    print("--- Starting Qdrant Vector Database Seeding ---")
    
    # Initialize embedder
    try:
        # THIS IS THE CORRECT BLOCK
        embedder = SentenceTransformerEmbedder(
            id=EMBEDDING_MODEL
        )
        print(f"Initialized embedder: {EMBEDDING_MODEL}")
    except Exception as e:
        print(f"Error initializing embedder: {e}")
        return
    
    # Initialize Qdrant client
    try:
        qdrant_client = QdrantClient(url=QDRANT_URL)
        print(f"Connected to Qdrant at {QDRANT_URL}")
    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")
        return
    
    # Initialize MongoDB for metadata storage
    try:
        mongo_client = pymongo.MongoClient(MONGO_URL)
        db = mongo_client[DATABASE_NAME]
        knowledge_metadata_col = db["knowledge_metadata"]
        print(f"Connected to MongoDB at {MONGO_URL}")
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return
    
    try:
        # Delete existing collection if it exists
        try:
            qdrant_client.delete_collection(QDRANT_COLLECTION)
            print(f"Deleted existing collection: {QDRANT_COLLECTION}")
        except:
            pass
        
        # Create new collection
        qdrant_client.create_collection(
            collection_name=QDRANT_COLLECTION,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSIONS,
                distance=Distance.COSINE
            )
        )
        print(f"Created collection: {QDRANT_COLLECTION}")
        
        # Create knowledge base directories and sample documents
        base_dir = create_knowledge_base_directories()
        create_sample_documents(base_dir)
        
        # Initialize document readers
        readers = {
            'pdf': PDFReader(),
            'docx': DocxReader(),
            'txt': TextReader()
        }
        
        points = []
        metadata_docs = []
        point_id_counter = 1
        
        # Process documents from each directory
        for doc_type, reader in readers.items():
            doc_dir = base_dir / {"pdf": "pdfs", "docx": "docx", "txt": "texts"}[doc_type]
            
            if not doc_dir.exists():
                continue
                
            extensions = {
                'pdf': ['.pdf'],
                'docx': ['.docx', '.doc'],
                'txt': ['.txt', '.md']
            }
            
            for ext in extensions[doc_type]:
                for file_path in doc_dir.glob(f"*{ext}"):
                    try:
                        print(f"Processing {file_path}")
                        
                        # Read and chunk document
                        documents = reader.read(file_path)
                        
                        # --- START: BATCH EMBEDDING ---
                        contents = [doc.content for doc in documents]
                        if not contents:
                            continue
                        embeddings = embedder.get_embedding(contents)
                        # --- END: BATCH EMBEDDING ---

                        for i, doc in enumerate(documents):
                            # Get pre-calculated embedding
                            embedding = embeddings[i]
                            
                            # Create unique IDs
                            qdrant_id = str(uuid.uuid4())
                            mongo_id = f"doc_{point_id_counter}_{i}"
                            
                            # Prepare metadata
                            metadata = {
                                "file_path": str(file_path),
                                "file_name": file_path.name,
                                "document_type": doc_type,
                                "chunk_index": i,
                                "total_chunks": len(documents),
                                "mongo_doc_id": mongo_id,
                                "qdrant_point_id": qdrant_id,
                                "created_at": datetime.now(timezone.utc).isoformat(),
                                "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                            }
                            
                            # Add document-specific metadata if available
                            if hasattr(doc, 'meta') and doc.meta:
                                metadata.update(doc.meta)
                            
                            # Create Qdrant point
                            point = PointStruct(
                                id=qdrant_id,
                                vector=embedding,
                                payload=metadata
                            )
                            points.append(point)
                            
                            # Prepare MongoDB metadata document
                            mongo_doc = {
                                "_id": mongo_id,
                                "qdrant_point_id": qdrant_id,
                                "file_path": str(file_path),
                                "file_name": file_path.name,
                                "document_type": doc_type,
                                "chunk_index": i,
                                "total_chunks": len(documents),
                                "content": doc.content,
                                "content_length": len(doc.content),
                                "metadata": metadata,
                                "created_at": datetime.now(timezone.utc),
                                "updated_at": datetime.now(timezone.utc)
                            }
                            metadata_docs.append(mongo_doc)
                            
                        point_id_counter += 1
                            
                    except Exception as e:
                        print(f"Error processing {file_path}: {e}")
                        continue
        
        # Insert points into Qdrant
        if points:
            print(f"Inserting {len(points)} points into Qdrant...")
            qdrant_client.upsert(
                collection_name=QDRANT_COLLECTION,
                points=points
            )
            print(f"Successfully inserted {len(points)} points into Qdrant")
        
        # Insert metadata into MongoDB
        if metadata_docs:
            print(f"Inserting {len(metadata_docs)} metadata documents into MongoDB...")
            knowledge_metadata_col.delete_many({})  # Clear existing
            knowledge_metadata_col.insert_many(metadata_docs)
            print(f"Successfully inserted {len(metadata_docs)} metadata documents into MongoDB")
        
        # Verify collections
        collection_info = qdrant_client.get_collection(QDRANT_COLLECTION)
        mongo_count = knowledge_metadata_col.count_documents({})
        
        print(f"\n--- Seeding Complete ---")
        print(f"Qdrant collection '{QDRANT_COLLECTION}' points: {collection_info.points_count}")
        print(f"MongoDB 'knowledge_metadata' documents: {mongo_count}")
        print(f"Embedding model: {EMBEDDING_MODEL}")
        print(f"Vector dimensions: {EMBEDDING_DIMENSIONS}")
        
    except Exception as e:
        print(f"Error during seeding: {e}")
    finally:
        if 'mongo_client' in locals():
            mongo_client.close()
        print("--- Qdrant Seeding Finished ---")

if __name__ == "__main__":
    seed_qdrant_database()