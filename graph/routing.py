from graph.state import GraphState, PlannerDecision, GraphStatus
from core.logging import get_logger
logger = get_logger()

def route_after_planner(state: GraphState) -> str:
    """
    Decide path after planner node.
    """
    thread_id = state.get("thread_id")
    user_id = state.get("user_id")
    decision = state["planner_decision"]
    if state["planner_decision"] == PlannerDecision.DIRECT:
        route = "direct_answer"
        logger.debug(
            f"Routing after planner: {route} (simple query, no research needed)",
            extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "decision": decision,
                "route": route
            }
        )
        return route
    route = "plan_writer"
    logger.debug(
        f"Routing after planner: {route} (complex query, research needed)",
        extra={
            "thread_id": thread_id,
            "user_id": user_id,
            "decision": decision,
            "route": route
        }
    )
    return route


def route_after_researcher(state: GraphState) -> str:
    """
    Decide whether to continue researching or verify.
    """
    thread_id = state.get("thread_id")
    user_id = state.get("user_id")
    route = "verifier"
    logger.debug(
        f"Routing after researcher: {route}",
        extra={
            "thread_id": thread_id,
            "user_id": user_id,
            "route": route
        }
    )
    return route


def route_after_verifier(state: GraphState) -> str:
    thread_id = state.get("thread_id")
    user_id = state.get("user_id")
    status = state["graph_status"]

    if status == GraphStatus.RESEARCHING:
        route = "retry_fanout"
        logger.debug(
            f"Routing after verifier: {route} (retrying failed tasks)",
            extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "graph_status": status,
                "route": route
            }
        )
        return route

    if status == GraphStatus.VERIFYING:
        route = "editor"
        logger.debug(
            f"Routing after verifier: {route} (all tasks complete, synthesizing)",
            extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "graph_status": status,
                "route": route
            }
        )
        return route

    route = "__end__"
    logger.debug(
        f"Routing after verifier: {route} (graph failed or completed)",
        extra={
            "thread_id": thread_id,
            "user_id": user_id,
            "graph_status": status,
            "route": route
        }
    )
    return route