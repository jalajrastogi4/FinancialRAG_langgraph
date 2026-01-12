from langchain.messages import HumanMessage
from graph.state import GraphState, GraphStatus
from agents.editor_agent import run_editor_agent
from core.logging import get_logger

logger = get_logger()


def editor_node(state: GraphState) -> GraphState:
    thread_id = state.get("thread_id")
    user_id = state.get("user_id")

    log = logger.bind(thread_id=thread_id, user_id=user_id)
    
    log.info(
        "Editor node started"
    )

    failed = state.get("partial_failures", [])

    if failed:
        missing_sections = "\n".join(
            f"- {t['question']}" for t in failed
        )

        instruction = (
            "Some research themes could not be completed.\n\n"
            "Proceed with synthesizing the available research files.\n"
            "Explicitly note that the following sections are incomplete or missing:\n"
            f"{missing_sections}\n\n"
            "Do NOT fabricate missing information."
        )
    else:
        instruction = (
            "All research themes were successfully completed.\n"
            "Synthesize the research into a comprehensive report."
        )

    sub_state = {
        "messages": [
            HumanMessage(content=instruction)
        ],
        "user_id": user_id,
        "thread_id": thread_id,
    }

    run_editor_agent(sub_state)

    state["graph_status"] = GraphStatus.COMPLETED
    log.info("Final report generated")
    
    return state