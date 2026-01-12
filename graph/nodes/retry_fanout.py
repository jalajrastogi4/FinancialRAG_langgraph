from langgraph.types import Send, Command
from graph.state import GraphState, TaskStatus
from core.config import settings
from core.logging import get_logger

logger = get_logger()


def retry_fanout_node(state: GraphState):
    logger.info("Retry fan-out node started")

    tasks = state.get("research_tasks") or []
    if not tasks:
        logger.warning("Retry fan-out called with no research tasks")
        return []

    sends = []

    for task in tasks:
        if (
            task["status"] == TaskStatus.FAILED
            and task["retries"] < settings.MAX_RETRIES_PER_THEME
        ):
            task["retries"] += 1
            task["status"] = TaskStatus.PENDING

            logger.info(
                f"Retrying theme {task['theme_id']} "
                f"(attempt {task['retries']})"
            )

            sends.append(
                Send(
                    "researcher",
                    {
                        "messages": state["messages"],
                        "current_task": task,
                        # "user_id": state.get("user_id"),
                        # "thread_id": state.get("thread_id"),
                        # "tool_budgets": dict(state.get("tool_budgets", {})),
                    },
                )
            )

    logger.info(f"Retry fan-out spawned {len(sends)} retries")
    return Command(goto=sends)