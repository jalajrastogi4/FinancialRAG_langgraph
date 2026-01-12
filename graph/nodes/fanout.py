from langgraph.types import Send, Command
from graph.state import GraphState
from core.logging import get_logger

logger = get_logger()


def fanout_node(state: GraphState):
    logger.info("Fan-out node started")

    tasks = state.get("research_tasks") or []
    if not tasks:
        logger.warning("Fan-out called with no research tasks")
        return []

    sends = []

    for task in tasks:
        sends.append(
            Send(
                "researcher",
                {
                    "messages": state["messages"],
                    "current_task": task,
                },
            )
        )

    logger.info(f"Fan-out created {len(sends)} parallel researcher branches")
    return Command(goto=sends)