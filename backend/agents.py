# agents.py
from typing import Dict
from agno.agent import Agent
from agno.team import Team
from agno.tools.serper import SerperTools
from agno.tools.python import PythonTools
from agno.tools.file import FileTools
from config import (
    BASE_MODEL, 
    agent_storage, 
    memory, 
    legal_knowledge_base, 
    vector_db,
    KNOWLEDGE_SEARCH_CONFIG
)

class LegalAgentSystem:
    def __init__(self):
        self.agents = self._initialize_agents()
        self.team = self._create_agent_team()

    def _initialize_agents(self) -> Dict[str, Agent]:
        """Initialize all specialized legal agents with knowledge base."""
        common_config = {
            "model": BASE_MODEL,
            "storage": agent_storage,
            "memory": memory,
            "knowledge": legal_knowledge_base,
            "search_knowledge": True,  
            "add_history_to_messages": True,
            "num_history_runs": 5,
            "enable_user_memories": True,
            "enable_session_summaries": True,
            "enable_agentic_memory": True,
            "show_tool_calls": True,
            "markdown": True,
        }

        search_instruction = (
            "To search the web for up-to-date information, use the `search` tool. "
            "For legal research, first search your knowledge base for relevant legal documents, "
            "precedents, and regulations. If additional current information is needed, "
            "then use web search. For example: `search(query='latest intellectual property laws in Malaysia')`."
        )

        knowledge_instruction = (
            "You have access to a comprehensive legal knowledge base containing legal documents, "
            "case law, regulations, and legal precedents. Always search your knowledge base first "
            "before suggesting web searches for more current information."
        )

        return {
            "researcher": Agent(
                name="LegalResearcher",
                instructions=(
                    f"You are a Legal Research Specialist with access to extensive legal databases. "
                    f"Your primary goal is to research legal precedents, statutes, and case law. "
                    f"{knowledge_instruction} {search_instruction} "
                    f"Focus on providing accurate legal research with proper citations and references. "
                    f"When you find relevant information in your knowledge base, provide the source "
                    f"document information along with MongoDB document IDs for cross-referencing."
                ),
                tools=[SerperTools(), FileTools()],
                **common_config
            ),
            "contract_analyzer": Agent(
                name="ContractAnalyzer",
                instructions=(
                    f"You are a Contract Analysis Expert specializing in contract law with expertise "
                    f"in risk assessment and legal document analysis. {knowledge_instruction} "
                    f"Your primary goal is to analyze contracts, identify risks, suggest improvements, "
                    f"and compare against standard contract templates and clauses in your knowledge base. "
                    f"Always reference similar contract provisions from your knowledge base when making "
                    f"recommendations and provide document IDs for MongoDB cross-referencing."
                ),
                tools=[PythonTools(), FileTools()],
                **common_config
            ),
            "compliance_advisor": Agent(
                name="ComplianceAdvisor",
                instructions=(
                    f"You are a Legal Compliance Specialist with access to regulatory documents "
                    f"and compliance frameworks. {knowledge_instruction} {search_instruction} "
                    f"Your primary goal is to provide guidance on regulatory compliance and legal "
                    f"requirements. Cross-reference current regulations in your knowledge base with "
                    f"the latest updates from web searches. Provide document IDs and metadata for "
                    f"MongoDB integration when referencing compliance documents."
                ),
                tools=[SerperTools(), PythonTools()],
                **common_config
            ),
            "document_drafter": Agent(
                name="DocumentDrafter",
                instructions=(
                    f"You are a Legal Document Specialist specializing in legal writing and document "
                    f"preparation. {knowledge_instruction} Your primary goal is to draft legal documents, "
                    f"agreements, and legal correspondence using templates and examples from your "
                    f"knowledge base. Always reference similar documents in your knowledge base when "
                    f"drafting new documents and maintain consistency with established legal language "
                    f"patterns. Store drafted documents with proper metadata linking to source templates."
                ),
                tools=[FileTools(), PythonTools()],
                **common_config
            ),
            "legal_advisor": Agent(
                name="LegalAdvisor",
                instructions=(
                    f"You are a Senior Legal Consultant with broad expertise and access to comprehensive "
                    f"legal knowledge base. {knowledge_instruction} {search_instruction} "
                    f"Your primary goal is to coordinate legal enquiries and provide comprehensive legal "
                    f"guidance by synthesizing information from your knowledge base with current legal "
                    f"developments. When providing advice, always cite relevant documents from your "
                    f"knowledge base and provide MongoDB document IDs for detailed cross-referencing. "
                    f"Coordinate with other specialist agents when complex multi-domain legal issues arise."
                ),
                tools=[SerperTools(), FileTools()],
                **common_config
            )
        }

    def _create_agent_team(self) -> Team:
        """Create a coordinated team of all agents with shared knowledge base."""
        return Team(
            model=BASE_MODEL,
            members=list(self.agents.values()),
            storage=agent_storage,
            memory=memory,
            knowledge=legal_knowledge_base,
            search_knowledge=True,
            knowledge_filters=KNOWLEDGE_SEARCH_CONFIG,
            show_tool_calls=True,
            markdown=True,
            instructions=(
                "You are a coordinated team of legal specialists with access to a comprehensive "
                "legal knowledge base. Work together to provide accurate, well-researched legal "
                "assistance. Always search the knowledge base first, then supplement with current "
                "information as needed. Maintain cross-references between Qdrant vector searches "
                "and MongoDB session data for comprehensive case tracking."
            )
        )

legal_system = LegalAgentSystem()