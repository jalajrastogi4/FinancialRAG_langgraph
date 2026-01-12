import os
import subprocess
import sys
import textwrap

from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_qdrant import QdrantVectorStore, RetrievalMode, FastEmbedSparse
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from qdrant_client.models import Filter, FieldCondition, MatchValue
from langchain_core.tools import tool

from tools.schema import ChunkMetadata
from agents.llm import get_llm
from tools.vectorstore import VectorStore
from core.config import settings
from core.logging import get_logger

logger = get_logger()


_llm = None
_vector_store = None


def _get_llm():
    """Lazy initialization of LLM."""
    global _llm
    if _llm is None:
        _llm = get_llm()
    return _llm
def _get_vector_store():
    """Lazy initialization of vector store."""
    global _vector_store
    if _vector_store is None:
        vector_store_manager = VectorStore()
        _vector_store = vector_store_manager.get_vectorstore()
    return _vector_store

# llm = get_llm()
# vector_store_manager = VectorStore()
# vector_store = vector_store_manager.get_vectorstore()

def extract_filters(user_query: str):

    prompt = f"""
            Extract metadata filters from the query. Return None for fields not mentioned.

                <USER QUERY STARTS>
                {user_query}
                </USER QUERY ENDS>

                #### EXAMPLES
                COMPANY MAPPINGS:
                - Amazon/AMZN -> amazon
                - Google/Alphabet/GOOGL/GOOG -> google
                - Apple/AAPL -> apple
                - Microsoft/MSFT -> microsoft
                - Tesla/TSLA -> tesla
                - Nvidia/NVDA -> nvidia
                - Meta/Facebook/FB -> meta

                DOC TYPE:
                - Annual report -> 10-k
                - Quarterly report -> 10-q
                - Current report -> 8-k

                EXAMPLES:
                "Amazon Q3 2024 revenue" -> {{"company_name": "amazon", "doc_type": "10-q", "fiscal_year": 2024, "fiscal_quarter": "q3"}}
                "Apple 2023 annual report" -> {{"company_name": "apple", "doc_type": "10-k", "fiscal_year": 2023}}
                "Tesla profitability" -> {{"company_name": "tesla"}}

                Extract metadata based on the user query only:
            """

    structurerd_llm = _get_llm().with_structured_output(ChunkMetadata)

    try:
        logger.info("Extracting filters from user query")
        metadata = structurerd_llm.invoke(prompt)

        if metadata:
            filters = metadata.model_dump(exclude_none=True)
        else:
            filters = {}

        return filters
    except Exception as e:
        logger.exception("Error running extract filters tool")
        raise e


@tool
def hybrid_search(query: str, k: int = 5):
    """
    Search historical financial documents (SEC filings: 10-K, 10-Q, 8-K) using hybrid search.

    **IMPORTANT: This is the PRIMARY tool for financial research.**
    **ALWAYS call this tool FIRST for ANY financial question unless:**
    - User explicitly asks for "current", "live", "real-time", or "latest" market data
    - User asks about current stock prices or today's market information

    This tool searches through:
    - Historical SEC filings (10-K annual reports, 10-Q quarterly reports)
    - Financial statements, revenue, expenses, cash flow data
    - Company performance metrics from past quarters and years
    - Automatically extracts filters (company, year, quarter, doc type) from your query

    Use this for queries about:
    - Historical revenue, profit, expenses ("What was Amazon's revenue in Q1 2024?")
    - Year-over-year or quarter-over-quarter comparisons
    - Financial metrics from SEC filings
    - Any historical financial data

    Args:
        query: Natural language search query (e.g., "Amazon Q1 2024 revenue")
        k: Number of results to return (default: 5)

    Returns:
        List of Document objects with page content and metadata (source_file, page_number, etc.)
    """

    try:
        logger.info("Running hybrid search tool")
        filters = extract_filters(query)

        qdrant_filter = None

        if filters:
            condition = [
                FieldCondition(key=f"metadata.{key}", match=MatchValue(value=value))
                for key, value in filters.items()
            ]

            qdrant_filter = Filter(must=condition)

        results = _get_vector_store().similarity_search(query=query, k=k, filter=qdrant_filter)

        return results
    except Exception as e:
        logger.exception("Error running hybrid search tool")
        raise e



import subprocess
import sys

@tool
def live_finance_researcher(query: str):
    """
    Research live stock data using Yahoo Finance MCP.
    
    Use this tool to get:
    - Current stock prices and real-time market data
    - Latest financial news
    - Stock recommendations and analyst ratings
    - Option chains and expiration dates
    - Recent stock actions (splits, dividends)
    
    Args:
        query: The financial research question about current market data
    
    Returns:
        Research results from Yahoo Finance
    """

    try:
        logger.info("Running live finance researcher tool")
        script = textwrap.dedent("""
import sys
import asyncio
from tools.yahoo_mcp import finance_research

if __name__ == "__main__":
    query = sys.argv[1]
    result = asyncio.run(finance_research(query))
    print(result)
""")
        result = subprocess.run(
            [sys.executable, '-c', script, query], 
            capture_output=True, 
            text=True,
            timeout=30
            )

        if result.returncode != 0:
            logger.error(f"Subprocess failed with error: {result.stderr}")
            return f"Error: Failed to fetch live finance data. {result.stderr}"

        return result.stdout

    except subprocess.TimeoutExpired:
        logger.error("Live finance researcher timed out after 30 seconds")
        return "Error: Request timed out. Please try again with a simpler query."

    except Exception as e:
        logger.exception("Error running live finance researcher tool")
        return f"Error: {str(e)}"


@tool
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.

    Use this tool after each search to analyze results and plan next steps systematically.
    This creates a deliberate pause in the research workflow for quality decision-making.

    When to use:
    - After receiving search results: What key information did I find?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Analysis of current findings - What concrete information have I gathered?
    2. Gap assessment - What crucial information is still missing?
    3. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    4. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    return f"Reflection recorded: {reflection}"