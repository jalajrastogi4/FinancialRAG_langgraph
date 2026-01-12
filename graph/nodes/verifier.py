from graph.state import GraphState, TaskStatus, GraphStatus
from core.config import settings
from core.logging import get_logger

logger = get_logger()


def verifier_node(state: GraphState) -> GraphState:
    thread_id = state.get("thread_id")
    user_id = state.get("user_id")
    log = logger.bind(thread_id=thread_id, user_id=user_id)

    log.info(
        "Verifier node started"
    )

    tasks = state.get("research_tasks", [])

    successful = [t for t in tasks if t["status"] == TaskStatus.SUCCESS]
    failed = [t for t in tasks if t["status"] == TaskStatus.FAILED]

    retryable = [
        t for t in failed if t["retries"] < settings.MAX_RETRIES_PER_THEME
    ]

    log.info(
        f"Verification summary: {len(successful)} successful, {len(failed)} failed, "
        f"{len(retryable)} retryable",
        extra={
            "total_tasks": len(tasks),
            "successful_count": len(successful),
            "failed_count": len(failed),
            "retryable_count": len(retryable)
        }
    )

    if not successful and not retryable:
        state["graph_status"] = GraphStatus.FAILED
        state["last_error"] = "All research tasks failed after retries"

        log.error(
            "All research tasks failed after retries. Ending graph execution.",
            extra={
                "graph_status": GraphStatus.FAILED,
                "failed_tasks": [t["theme_id"] for t in failed]
            }
        )

        return state

    if retryable:
        retryable_theme_ids = [t["theme_id"] for t in retryable]
        
        log.info(
            f"Retrying {len(retryable)} failed tasks: themes {retryable_theme_ids}",
            extra={
                "graph_status": GraphStatus.RESEARCHING,
                "retryable_count": len(retryable),
                "retryable_theme_ids": retryable_theme_ids
            }
        )

        state["graph_status"] = GraphStatus.RESEARCHING
        return state

    state["graph_status"] = GraphStatus.VERIFYING
    state["partial_failures"] = failed

    if failed:
        failed_theme_ids = [t["theme_id"] for t in failed]
        log.warning(
            f"Proceeding to editor with {len(failed)} partial failures: themes {failed_theme_ids}",
            extra={
                "graph_status": GraphStatus.VERIFYING,
                "partial_failures_count": len(failed),
                "failed_theme_ids": failed_theme_ids
            }
        )
    else:
        log.info(
            "All research tasks completed successfully. Proceeding to editor.",
            extra={
                "graph_status": GraphStatus.VERIFYING,
                "all_successful": True
            }
        )

    return state