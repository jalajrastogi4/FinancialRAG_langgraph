from typing import Annotated
from langgraph.prebuilt import InjectedState
from langchain.agents import create_agent
from langchain.messages import AIMessage
from langchain_core.tools import tool

from agents.llm import get_llm
from prompts.researcher import RESEARCHER_PROMPT
from tools.file_tools import ls, read_file, write_file
from tools.rag_tools import hybrid_search, live_finance_researcher
from tools.file_tools import DeepAgentState
from tools.rate_limiters import get_rate_limiter
from tools.utils import enforce_budget
from tools.tool_callback_handler import ToolErrorLogger
from core.logging import get_logger
from core.observability import get_langfuse_handler

logger = get_logger()


@tool(parse_docstring=True)
def hardened_hybrid_search(
    query: str, 
    k: int = 5,
    state: Annotated[DeepAgentState, InjectedState] = None
    ):
    """
    Hybrid search with rate limiting and budget enforcement.

    Args:
        query: Natural language financial search query.
        k: Number of search results to return.
        state: Injected agent state containing tool budgets.

    Returns:
        A list of relevant financial documents.
    """
    logger.debug(
        "Entering hardened_hybrid_search",
        extra={
            "query": query,
            "k": k,
            "tool_budgets": state.get("tool_budgets") if state else None,
            "thread_id": state.get("thread_id") if state else None,
            "user_id": state.get("user_id") if state else None,
        },
    )
    try:
        logger.info("Hardening hybrid search tool")
        if state is None:
            return "Internal error: state not available."

        # Enforce budget
        budgets = state.get("tool_budgets", {})
        # enforce_budget(state, "hybrid_search")
        # print("===== Budget =====")
        # print(budgets.get("hybrid_search"))
        # print("===== End Budget =====")

        if budgets.get("hybrid_search", float("inf")) <= 0:
            return (
                "Hybrid search budget exhausted. "
                "Use previously retrieved information or proceed without further searches."
            )

        budgets["hybrid_search"] -= 1

        # Enforce rate limit (example: 2 QPS)
        limiter = get_rate_limiter("hybrid_search", rate_per_sec=2)
        limiter.acquire()

        logger.debug("Calling hybrid_search")
        results = hybrid_search.invoke({"query": query, "k": k})
        logger.debug(f"Hybrid search returned {len(results)} documents")

        formatted = "\n\n".join(
            f"Source: {doc.metadata.get('source_file', 'unknown')}\n{doc.page_content}"
            for doc in results[:5]
        )

        return (
            "Here are relevant excerpts from financial filings:\n\n"
            + formatted
        )
    except Exception as e:
        logger.exception(
            "hardened_hybrid_search FAILED",
            extra={
                "query": query,
                "tool_budgets": state.get("tool_budgets") if state else None,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        raise
    

@tool(parse_docstring=True)
def hardened_live_finance_researcher(
    query: str,
    state: Annotated[DeepAgentState, InjectedState] = None,
    ):
    """
    Live finance researcher with rate limiting and budget enforcement.

    Args:
        query: Financial query requiring live market data.

    Returns:
        Live financial research results.
    """
    logger.debug(
        "Entering hardened_live_finance_researcher",
        extra={
            "query": query,
            "tool_budgets": state.get("tool_budgets") if state else None,
            "thread_id": state.get("thread_id") if state else None,
            "user_id": state.get("user_id") if state else None,
        },
    )
    try:
        logger.info("Hardening live finance researcher tool")
        # state = kwargs.get("state")
        if state is None:
            return "Internal error: state not available."

        budgets = state.get("tool_budgets", {})
        # enforce_budget(state, "live_finance_researcher")
        if budgets.get("live_finance_researcher", float("inf")) <= 0:
            return (
                "Live finance researcher budget exhausted. "
                "Use previously retrieved information or proceed without further searches."
            )

        budgets["live_finance_researcher"] -= 1

        # More conservative rate limit (example: 1 QPS)
        limiter = get_rate_limiter("live_finance_researcher", rate_per_sec=1)
        limiter.acquire()

        logger.debug("Calling live_finance_researcher")
        results = live_finance_researcher.invoke({"query": query})
        logger.debug(f"Live finance researcher returned {len(results)} documents")
        
        return results
    except Exception as e:
        logger.exception(
            "hardened_live_finance_researcher FAILED",
            extra={
                "query": query,
                "tool_budgets": state.get("tool_budgets") if state else None,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        raise


def create_researcher_agent():
    """
    Create the Researcher agent.
    """
    llm = get_llm()

    agent = create_agent(
        model=llm,
        tools=[
            ls,
            read_file,
            write_file,
            # hybrid_search,
            hardened_hybrid_search,
            # live_finance_researcher,
            hardened_live_finance_researcher,
        ],
        system_prompt=RESEARCHER_PROMPT,
        state_schema=DeepAgentState,
    )

    return agent


def run_researcher_agent(sub_state: DeepAgentState):
    """
    Run the Researcher agent with a prepared sub-state.
    """
    thread_id = sub_state.get("thread_id")
    user_id = sub_state.get("user_id")

    log = logger.bind(thread_id=thread_id, user_id=user_id)
    
    log.info(
        "Running Researcher agent",
    )

    callbacks = []
    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            callbacks.append(langfuse_handler)
            log.debug("Langfuse handler attached to researcher agent")
    except Exception as e:
        log.warning(f"Failed to attach Langfuse handler to researcher: {e}")

    callbacks.append(ToolErrorLogger())
    agent = create_researcher_agent()

    config = {"callbacks": callbacks, "tags": ["finance", "researcher_agent"]} if callbacks else {}
    result = agent.invoke(sub_state, config=config)

    return result