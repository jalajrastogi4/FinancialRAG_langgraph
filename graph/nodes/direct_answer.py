from langchain.messages import AIMessage
from agents.llm import get_llm
from graph.state import GraphState, GraphStatus
from core.logging import get_logger

logger = get_logger()


def direct_answer_node(state: GraphState) -> GraphState:
    logger.info("Direct answer node started")

    try:
        llm = get_llm()

        logger.info("LLM initialized successfully")
        response = llm.invoke(state["messages"])

        state["messages"].append(response)
        state["graph_status"] = GraphStatus.COMPLETED

        return state
    except Exception as e:
        logger.exception(
            "Error running direct answer node",
            extra={"thread_id": state["thread_id"], "user_id": state["user_id"]}
        )
        raise e