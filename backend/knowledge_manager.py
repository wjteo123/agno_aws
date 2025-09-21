# knowledge_manager.py
import os
import uuid
import asyncio
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import UploadFile
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, Filter, FieldCondition, MatchValue
import pymongo
from agno.embedder.sentence_transformer import SentenceTransformerEmbedder
from agno.knowledge.pdf import PDFReader
from agno.knowledge.docx import DocxReader
from agno.knowledge.text import TextReader

# Import configuration
from config import (
    vector_db, embedder, MONGO_URL, DATABASE_NAME,
    KNOWLEDGE_BASE_DIR, QDRANT_URL, logger
)

class KnowledgeManager:
    """Manages knowledge base operations including document upload, search, and maintenance."""

    def __init__(self):
        self.qdrant_client = QdrantClient(url=QDRANT_URL)
        self.mongo_client = pymongo.MongoClient(MONGO_URL)
        self.db = self.mongo_client[DATABASE_NAME]
        self.metadata_collection = self.db["knowledge_metadata"]
        
        # Document readers
        self.readers = {
            'pdf': PDFReader(),
            'docx': DocxReader(),
            'text': TextReader()
        }
        
        # Ensure knowledge base directory exists
        Path(KNOWLEDGE_BASE_DIR).mkdir(parents=True, exist_ok=True)

    async def search_knowledge(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.7,
        document_type: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search the knowledge base for relevant documents."""
        try:
            # Generate embedding for the query
            query_embedding = embedder.get_embedding(query)
            
            # Build filter conditions
            filter_conditions = []
            if document_type:
                filter_conditions.append(
                    FieldCondition(key="document_type", match=MatchValue(value=document_type))
                )
            if category:
                filter_conditions.append(
                    FieldCondition(key="category", match=MatchValue(value=category))
                )
            
            # Perform vector search
            search_result = self.qdrant_client.search(
                collection_name="legal_knowledge_base",
                query_vector=query_embedding,
                limit=limit,
                score_threshold=similarity_threshold,
                query_filter=Filter(must=filter_conditions) if filter_conditions else None
            )
            
            # Format results
            results = []
            for hit in search_result:
                # Get additional metadata from MongoDB
                mongo_doc = self.metadata_collection.find_one(
                    {"qdrant_point_id": hit.id}
                )
                
                result = {
                    "qdrant_point_id": hit.id,
                    "similarity_score": hit.score,
                    "content": hit.payload.get("content_preview", ""),
                    "file_name": hit.payload.get("file_name", ""),
                    "document_type": hit.payload.get("document_type", ""),
                    "category": hit.payload.get("category", "general"),
                    "chunk_index": hit.payload.get("chunk_index", 0),
                    "mongo_doc_id": hit.payload.get("mongo_doc_id", ""),
                    "metadata": hit.payload
                }
                
                # Add full content from MongoDB if available
                if mongo_doc:
                    result["full_content"] = mongo_doc.get("content", "")
                    result["mongo_metadata"] = mongo_doc.get("metadata", {})
                
                results.append(result)
            
            logger.info(f"Knowledge search for '{query}' returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Error in knowledge search: {e}")
            raise

    async def add_document(
        self,
        file: UploadFile,
        document_type: str,
        category: str = "general",
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Add a new document to the knowledge base."""
        try:
            # Generate unique document ID
            document_id = str(uuid.uuid4())
            
            # Create category directory
            category_dir = Path(KNOWLEDGE_BASE_DIR) / category
            category_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file
            file_path = category_dir / f"{document_id}_{file.filename}"
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Process document
            reader = self.readers.get(document_type)
            if not reader:
                raise ValueError(f"Unsupported document type: {document_type}")
            
            documents = reader.read(str(file_path))
            
            # --- START: BATCH EMBEDDING ---
            # 1. Get all content chunks into a list
            contents = [doc.content for doc in documents]
            
            # 2. Generate all embeddings in a single batch call
            if contents:
                embeddings = embedder.get_embedding(contents)
            else:
                embeddings = []
            # --- END: BATCH EMBEDDING ---

            points = []
            metadata_docs = []
            
            # 3. Loop through documents and their corresponding embeddings
            for i, doc in enumerate(documents):
                # Get the pre-calculated embedding
                embedding = embeddings[i]
                
                # Create unique IDs
                qdrant_id = str(uuid.uuid4())
                mongo_id = f"{document_id}_chunk_{i}"
                
                # Prepare metadata
                doc_metadata = {
                    "document_id": document_id,
                    "file_path": str(file_path),
                    "file_name": file.filename,
                    "document_type": document_type,
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(documents),
                    "mongo_doc_id": mongo_id,
                    "qdrant_point_id": qdrant_id,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "content_preview": doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
                }
                
                # Add custom metadata
                if metadata:
                    doc_metadata.update(metadata)
                
                # Add document-specific metadata
                if hasattr(doc, 'meta') and doc.meta:
                    doc_metadata.update(doc.meta)
                
                # Create Qdrant point
                point = PointStruct(
                    id=qdrant_id,
                    vector=embedding,
                    payload=doc_metadata
                )
                points.append(point)
                
                # Prepare MongoDB document
                mongo_doc = {
                    "_id": mongo_id,
                    "document_id": document_id,
                    "qdrant_point_id": qdrant_id,
                    "file_path": str(file_path),
                    "file_name": file.filename,
                    "document_type": document_type,
                    "category": category,
                    "chunk_index": i,
                    "total_chunks": len(documents),
                    "content": doc.content,
                    "content_length": len(doc.content),
                    "metadata": doc_metadata,
                    "created_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc)
                }
                metadata_docs.append(mongo_doc)
            
            # Insert into Qdrant
            if points:
                self.qdrant_client.upsert(
                    collection_name="legal_knowledge_base",
                    points=points
                )
            
            # Insert into MongoDB
            if metadata_docs:
                self.metadata_collection.insert_many(metadata_docs)
            
            logger.info(f"Added document {file.filename} with {len(documents)} chunks")
            
            return {
                "document_id": document_id,
                "chunks_created": len(documents),
                "file_path": str(file_path)
            }
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            raise

    async def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document and all its chunks from the knowledge base."""
        try:
            # Find all chunks for this document
            mongo_docs = list(self.metadata_collection.find({"document_id": document_id}))
            
            if not mongo_docs:
                raise ValueError(f"Document {document_id} not found")
            
            # Get Qdrant point IDs
            qdrant_ids = [doc["qdrant_point_id"] for doc in mongo_docs]
            
            # Delete from Qdrant
            self.qdrant_client.delete(
                collection_name="legal_knowledge_base",
                points_selector=qdrant_ids
            )
            
            # Delete from MongoDB
            self.metadata_collection.delete_many({"document_id": document_id})
            
            # Delete file if it exists
            if mongo_docs:
                file_path = Path(mongo_docs[0]["file_path"])
                if file_path.exists():
                    file_path.unlink()
            
            logger.info(f"Deleted document {document_id} with {len(mongo_docs)} chunks")
            
            return {
                "chunks_deleted": len(mongo_docs)
            }
            
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise

    async def list_documents(
        self,
        category: Optional[str] = None,
        document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List all documents in the knowledge base."""
        try:
            # Build query
            query = {}
            if category:
                query["category"] = category
            if document_type:
                query["document_type"] = document_type
            
            # Group by document_id to get unique documents
            pipeline = [
                {"$match": query},
                {
                    "$group": {
                        "_id": "$document_id",
                        "file_name": {"$first": "$file_name"},
                        "file_path": {"$first": "$file_path"},
                        "document_type": {"$first": "$document_type"},
                        "category": {"$first": "$category"},
                        "chunk_count": {"$sum": 1},
                        "created_at": {"$first": "$created_at"},
                        "updated_at": {"$max": "$updated_at"},
                        "total_content_length": {"$sum": "$content_length"}
                    }
                },
                {"$sort": {"created_at": -1}}
            ]
            
            documents = []
            for doc in self.metadata_collection.aggregate(pipeline):
                documents.append({
                    "document_id": doc["_id"],
                    "file_name": doc["file_name"],
                    "file_path": doc["file_path"],
                    "document_type": doc["document_type"],
                    "category": doc["category"],
                    "chunk_count": doc["chunk_count"],
                    "total_content_length": doc["total_content_length"],
                    "created_at": doc["created_at"],
                    "updated_at": doc["updated_at"]
                })
            
            return documents
            
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        try:
            # Qdrant stats
            collection_info = self.qdrant_client.get_collection("legal_knowledge_base")
            
            # MongoDB stats
            total_documents = len(list(self.metadata_collection.distinct("document_id")))
            total_chunks = self.metadata_collection.count_documents({})
            
            # Category stats
            category_pipeline = [
                {
                    "$group": {
                        "_id": "$category",
                        "document_count": {"$addToSet": "$document_id"},
                        "chunk_count": {"$sum": 1}
                    }
                },
                {
                    "$project": {
                        "category": "$_id",
                        "document_count": {"$size": "$document_count"},
                        "chunk_count": 1,
                        "_id": 0
                    }
                }
            ]
            categories = list(self.metadata_collection.aggregate(category_pipeline))
            
            # Document type stats
            type_pipeline = [
                {
                    "$group": {
                        "_id": "$document_type",
                        "document_count": {"$addToSet": "$document_id"},
                        "chunk_count": {"$sum": 1}
                    }
                },
                {
                    "$project": {
                        "document_type": "$_id",
                        "document_count": {"$size": "$document_count"},
                        "chunk_count": 1,
                        "_id": 0
                    }
                }
            ]
            document_types = list(self.metadata_collection.aggregate(type_pipeline))
            
            return {
                "total_documents": total_documents,
                "total_chunks": total_chunks,
                "qdrant_points": collection_info.points_count,
                "categories": categories,
                "document_types": document_types,
                "collection_status": collection_info.status
            }
            
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            raise

    async def reindex_all(self) -> Dict[str, Any]:
        """Reindex all documents in the knowledge base."""
        try:
            # Get all unique documents
            documents = await self.list_documents()
            
            total_processed = 0
            total_chunks = 0
            
            for doc in documents:
                # Delete existing chunks
                await self.delete_document(doc["document_id"])
                
                # Re-add document
                file_path = Path(doc["file_path"])
                if file_path.exists():
                    # Simulate UploadFile
                    with open(file_path, "rb") as f:
                        content = f.read()
                    
                    # Create a mock UploadFile object
                    class MockUploadFile:
                        def __init__(self, filename, content):
                            self.filename = filename
                            self._content = content
                        
                        async def read(self):
                            return self._content
                    
                    mock_file = MockUploadFile(doc["file_name"], content)
                    
                    result = await self.add_document(
                        file=mock_file,
                        document_type=doc["document_type"],
                        category=doc["category"]
                    )
                    
                    total_processed += 1
                    total_chunks += result["chunks_created"]
            
            logger.info(f"Reindexed {total_processed} documents with {total_chunks} chunks")
            
            return {
                "documents_processed": total_processed,
                "chunks_created": total_chunks
            }
            
        except Exception as e:
            logger.error(f"Error reindexing: {e}")
            raise