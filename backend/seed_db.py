# seed_db.py
"""
Seed MongoDB for the Legal Multi-Agent System:
- session documents -> collection "agent_data" (used by MongoDbAgentStorage)
- memory documents  -> collection "agent_memories" (used by MongoMemoryDb)
"""

import pymongo
import os
from dotenv import load_dotenv
from datetime import datetime, timezone

def seed_database():
    load_dotenv()

    MONGO_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "legal_agent_system")

    # Collections used by our app
    SESSION_COLLECTION = "agent_data"
    MEMORY_COLLECTION = "agent_memories"

    print("--- Starting Database Seeding ---")

    client = None
    try:
        client = pymongo.MongoClient(MONGO_URL)
        db = client[DATABASE_NAME]

        session_col = db[SESSION_COLLECTION]
        memory_col = db[MEMORY_COLLECTION]

        print(f"Connected to MongoDB at {MONGO_URL}, DB: {DATABASE_NAME}")

        # Clean collections
        print("Clearing existing documents...")
        session_col.delete_many({})
        memory_col.delete_many({})

        # Sample session documents
        session_docs = [
            {
                "_id": "session_contract_review_123",
                "session_id": "session_contract_review_123",
                "user_id": "user_jane_doe",
                "history": [
                    {"role": "user", "content": "Can you review this non-disclosure agreement for me?"},
                    {"role": "assistant", "content": "Certainly. I will check for standard clauses and potential risks."},
                    {"role": "user", "content": "The main points are the definition of confidential information and the term."},
                    {"role": "assistant", "content": "Understood. Analyzing those sections now..."}
                ],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "_id": "session_compliance_check_456",
                "session_id": "session_compliance_check_456",
                "user_id": "user_john_smith",
                "history": [
                    {"role": "user", "content": "What are the GDPR compliance requirements for a small e-commerce website?"},
                    {"role": "assistant", "content": "You need a clear privacy policy, lawful basis, and data subject request handling."}
                ],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]

        # Sample memories documents (format friendly to Memory V2 MongoMemoryDb)
        # The Memory V2 stores per-user memories; shape below is simple key/value list.
        memory_docs = [
            {
                "_id": "memories_user_jane_doe",
                "user_id": "user_jane_doe",
                "memories": [
                    {"memory": "Jane Doe is General Counsel for Innovatech Inc."},
                    {"memory": "Prefers summaries to be in bullet-point format."},
                    {"memory": "Innovatech Inc. operates in the European Union."}
                ],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            },
            {
                "_id": "memories_user_john_smith",
                "user_id": "user_john_smith",
                "memories": [
                    {"memory": "John Smith is a solo founder of a startup."},
                    {"memory": "Is primarily concerned with cost-effective legal solutions."}
                ],
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
        ]

        print(f"Inserting {len(session_docs)} session docs into '{SESSION_COLLECTION}'...")
        session_col.insert_many(session_docs)

        print(f"Inserting {len(memory_docs)} memory docs into '{MEMORY_COLLECTION}'...")
        memory_col.insert_many(memory_docs)

        print("Seed complete. Document counts:")
        print(f"  - {SESSION_COLLECTION}: {session_col.count_documents({})}")
        print(f"  - {MEMORY_COLLECTION}: {memory_col.count_documents({})}")

    except pymongo.errors.ConnectionFailure as e:
        print(f"Error: Could not connect to MongoDB. Details: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if client:
            client.close()
        print("--- Database Seeding Finished ---")


if __name__ == "__main__":
    seed_database()
