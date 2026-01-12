from graph.state import GraphState, GraphStatus
from tools.file_tools import _disk_path
from core.logging import get_logger

logger = get_logger()


def plan_writer_node(state: GraphState) -> GraphState:
    logger.info("PlanWriter node started")

    thematic_questions = state.get("thematic_questions", [])
    user_query = state["messages"][-1].content

    content = "# Research Plan\n\n"
    content += "## User Query\n"
    content += f"{user_query}\n\n"
    content += "## Thematic Questions\n\n"

    for idx, question in enumerate(thematic_questions, start=1):
        content += f"{idx}. {question}\n"

    try:
        logger.info("Writing research plan to disk")
        path = _disk_path(state, "research_plan.md")

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info(
            f"research_plan.md written with {len(thematic_questions)} thematic questions"
        )

        state["graph_status"] = GraphStatus.PLANNING
        return state
    except Exception as e:
        logger.exception("Error running plan writer node")
        raise e