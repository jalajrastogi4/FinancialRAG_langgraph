from langgraph.graph import StateGraph, END

from graph.state import GraphState
from graph.nodes.planner import planner_node
from graph.nodes.researcher import researcher_node
from graph.nodes.verifier import verifier_node
from graph.nodes.editor import editor_node
from graph.nodes.direct_answer import direct_answer_node
from graph.nodes.plan_writer import plan_writer_node
from graph.nodes.fanout import fanout_node
from graph.nodes.retry_fanout import retry_fanout_node
from graph.routing import (
    route_after_planner,
    route_after_researcher,
    route_after_verifier,
)

from persistence.checkpoint import get_checkpointer
from core.logging import get_logger

logger = get_logger()


def build_graph():
    logger.info("Building LangGraph")

    graph = StateGraph(GraphState)

    graph.add_node("planner", planner_node)
    graph.add_node("plan_writer", plan_writer_node)
    graph.add_node("researcher", researcher_node)
    graph.add_node("verifier", verifier_node)
    graph.add_node("editor", editor_node)
    graph.add_node("direct_answer", direct_answer_node)
    graph.add_node("fanout", fanout_node)
    graph.add_node("retry_fanout", retry_fanout_node)


    graph.set_entry_point("planner")
    # graph.add_edge("planner", "plan_writer")

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "direct_answer": "direct_answer",
            "plan_writer": "plan_writer",
        },
    )

    graph.add_edge("direct_answer", END)

    graph.add_edge("plan_writer", "fanout")
    # graph.add_edge("fanout", "researcher")
    graph.add_edge("researcher", "verifier")


    graph.add_conditional_edges(
        "verifier",
        route_after_verifier,
        {
            "retry_fanout": "retry_fanout",
            "editor": "editor",
            END: END,
        },
    )

    # graph.add_edge("retry_fanout", "researcher")

    graph.add_edge("editor", END)

    return graph.compile(
        checkpointer=get_checkpointer()
    )