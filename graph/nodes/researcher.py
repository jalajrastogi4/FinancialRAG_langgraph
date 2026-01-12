from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from langchain.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from graph.state import GraphState, TaskStatus, GraphStatus
from agents.researcher_agent import run_researcher_agent
from core.config import settings
from core.logging import get_logger
from tools.message_formatter import extract_text_from_message

logger = get_logger()


def researcher_node(state: GraphState, config: RunnableConfig) -> GraphState:
    task = state["current_task"]
    theme_id = task["theme_id"]
    identity = config.get("configurable", {})

    thread_id = identity.get("thread_id")
    user_id = identity.get("user_id")
    tool_budgets = dict(identity.get("tool_budgets", {}))

    logger.info(
        f"Researcher started for theme {theme_id}",
        extra={
            "thread_id": thread_id,
            "user_id": user_id,
            "theme_id": theme_id,
            "question": task["question"]
        }
    )

    instruction = (
        f"You are a financial research agent.\n\n"
        f"Research the following question thoroughly:\n"
        f"{task['question']}\n\n"
        f"You MUST:\n"
        f"- Use research tools as needed\n"
        f"- EVEN IF tools fail:\n"
        f"  - Write a clear explanation of the failure\n"
        f"  - Include error messages if available\n"
        f"- Write your findings to: {user_id}/{thread_id}/researcher/{task['file_hash']}_theme.md\n"
        f"- Write your sources to: {user_id}/{thread_id}/researcher/{task['file_hash']}_sources.txt\n"
        f"- Always produce a written response\n"
    )

    sub_state = {
        "messages": [
            HumanMessage(content=instruction)
        ],
        "user_id": user_id,
        "thread_id": thread_id,
        "tool_budgets": tool_budgets,
    }

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(run_researcher_agent, sub_state)

            result_state = future.result(timeout=settings.MAX_RESEARCH_TASK_TIMEOUT_SEC)
            message_count = len(result_state.get("messages", []))

            ai_outputs = [
                            extract_text_from_message(m)
                            for m in result_state.get("messages", [])
                            if isinstance(m, AIMessage)
                        ]

            logger.debug(
                "Researcher completed for theme {}. AI outputs:\n{}",
                theme_id,
                "\n\n".join(ai_outputs) if ai_outputs else "[NO AI OUTPUT]",
                extra={
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "theme_id": theme_id,
                    "status": "success",
                },
            )


            logger.info(
                f"Theme {theme_id} completed successfully. "
                f"Generated {message_count} messages.",
                extra={
                    "thread_id": thread_id,
                    "user_id": user_id,
                    "theme_id": theme_id,
                    "message_count": message_count,
                    "status": "success"
                }
            )

        task["status"] = TaskStatus.SUCCESS
        # logger.info(f"Theme {theme_id} completed successfully")

    except FuturesTimeout:
        task["status"] = TaskStatus.FAILED
        task["error"] = (
            f"Timeout after {settings.MAX_RESEARCH_TASK_TIMEOUT_SEC} seconds"
        )

        logger.exception(
            "Theme {} timed out after {}s",
            theme_id,
            settings.MAX_RESEARCH_TASK_TIMEOUT_SEC,
            extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "theme_id": theme_id,
                "status": "timeout",
                "timeout_sec": settings.MAX_RESEARCH_TASK_TIMEOUT_SEC
            }
        )

    except Exception as e:
        task["status"] = TaskStatus.FAILED
        task["error"] = str(e)

        logger.exception(
            "Theme {} failed",
            theme_id,
            extra={
                "thread_id": thread_id,
                "user_id": user_id,
                "theme_id": theme_id,
                "status": "failed",
                "error": str(e)
            }
        )

    return state