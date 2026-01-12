import os
from typing import Optional
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langfuse import get_client, observe

from graph.builder import build_graph
from graph.state import GraphState
from core.logging import get_logger
from core.config import settings
from core.observability import get_langfuse_handler

logger = get_logger()

os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_BASE_URL

@observe
def run_graph(
    query: str,
    thread_id: str,
    user_id: Optional[str] = None,
):
    """
    Execute the LangGraph with streaming output.
    """

    graph = build_graph()

    initial_state: GraphState = {
        "messages": [HumanMessage(content=query)],
        "thread_id": thread_id,
        "user_id": user_id,
        "graph_status": None,
        # "tool_budgets": {
        #     "hybrid_search": settings.HYBRID_SEARCH_TOOL_CALLS_PER_RESEARCHER,
        #     "live_finance_researcher": settings.LIVE_FINANCE_RESEARCHER_TOOL_CALLS_PER_RESEARCHER,
        # },
    }

    callbacks = []
    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            callbacks.append(langfuse_handler)
            logger.debug("Langfuse handler attached to graph execution")
    except Exception as e:
        logger.warning(f"Failed to attach Langfuse handler to graph: {e}")

    config = {
        "configurable": {
            "thread_id": thread_id,
            "user_id": user_id,
            "tool_budgets": {
                "hybrid_search": settings.HYBRID_SEARCH_TOOL_CALLS_PER_RESEARCHER,
                "live_finance_researcher": settings.LIVE_FINANCE_RESEARCHER_TOOL_CALLS_PER_RESEARCHER,
            },
        },
        "max_concurrency": settings.MAX_PARALLEL_RESEARCHERS,
        "callbacks": callbacks,
    }


    try:
        langfuse = get_client()

        log = logger.bind(thread_id=thread_id, user_id=user_id)

        log.info(
            f"Starting graph execution for thread_id={thread_id}, user_id={user_id}",
            )

        langfuse.update_current_trace(
            name="deep_finance_researcher",
            session_id=thread_id,
            user_id=user_id,
            tags=["finance"],
            input={
                "query": query,
                "thread_id": thread_id,
            },
        )

        for event in graph.stream(
            initial_state,
            config=config,
            stream_mode="messages",
        ):
            message = event[0] if isinstance(event, tuple) else event
            log.info(
                "Graph event received",
                extra={"event": event}
            )
            
            if isinstance(message, AIMessage) and message.content:
                print(message.content, end="", flush=True)

        log.info(
            f"Graph execution completed for thread_id={thread_id}",
        )

    except Exception as e:
        log.exception(
            "Error running graph"
        )
        raise e