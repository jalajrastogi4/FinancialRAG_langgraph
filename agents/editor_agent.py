from langchain.agents import create_agent
from langchain.messages import HumanMessage

from agents.llm import get_llm
from prompts.editor import EDITOR_PROMPT
from tools.file_tools import ls, read_file, write_file, cleanup_files
from tools.file_tools import DeepAgentState
from core.logging import get_logger
from core.observability import get_langfuse_handler

logger = get_logger()


def create_editor_agent():
    """
    Create the Editor agent.
    """
    llm = get_llm()

    agent = create_agent(
        model=llm,
        tools=[ls, read_file, write_file, cleanup_files],
        system_prompt=EDITOR_PROMPT,
        state_schema=DeepAgentState,
    )

    return agent


def run_editor_agent(state: DeepAgentState):
    """
    Run the Editor agent.
    """
    logger.info("Running Editor agent")

    callbacks = []
    try:
        langfuse_handler = get_langfuse_handler()
        if langfuse_handler:
            callbacks.append(langfuse_handler)
            logger.debug("Langfuse handler attached to editor agent")
    except Exception as e:
        logger.warning(f"Failed to attach Langfuse handler to editor: {e}")

    agent = create_editor_agent()

    sub_state = {
        "messages": [
            HumanMessage(
                content=(
                    "Read research_plan.md and all files in the researcher/ folder, "
                    "then synthesize everything into a comprehensive report.md file."
                )
            )
        ],
        "user_id": state.get("user_id"),
        "thread_id": state.get("thread_id"),
    }

    config = {"callbacks": callbacks, "tags": ["finance", "editor_agent"]} if callbacks else {}
    agent.invoke(sub_state, config=config)

    return sub_state