from langchain.messages import SystemMessage, HumanMessage, AIMessage
from graph.state import (
    GraphState,
    PlannerDecision,
    GraphStatus,
    TaskStatus,
    PlannerOutput,
)
# from prompts.orchestrator import ORCHESTRATOR_PROMPT
from prompts.planner import PLANNER_PROMPT
from tools.file_tools import generate_hash
from core.logging import get_logger
from agents.llm import get_llm

logger = get_logger()

def planner_node(state: GraphState) -> GraphState:
    logger.info("Planner node started")

    llm = get_llm()

    user_query = state["messages"][-1].content

    structured_llm = llm.with_structured_output(PlannerOutput)

    try:
        
        logger.info("Planner node started")

        result: PlannerOutput = structured_llm.invoke(
            [
                SystemMessage(content=PLANNER_PROMPT),
                HumanMessage(content=user_query),
            ]
        )

        logger.debug(f"Planner output: {result}")

        if result.decision == PlannerDecision.DIRECT:
            state["planner_decision"] = PlannerDecision.DIRECT
            state["graph_status"] = GraphStatus.COMPLETED
            return state


        tasks = []
        for idx, question in enumerate(result.thematic_questions, start=1):
            tasks.append(
                {
                    "theme_id": idx,
                    "question": question,
                    "file_hash": generate_hash(f"{idx}_{question}"),
                    "status": TaskStatus.PENDING,
                    "retries": 0,
                    "error": None,
                    "user_id": state.get("user_id"),
                    "thread_id": state.get("thread_id"),
                }
            )

        state["planner_decision"] = PlannerDecision.RESEARCH
        state["thematic_questions"] = result.thematic_questions
        state["research_tasks"] = tasks
        state["graph_status"] = GraphStatus.PLANNING

        logger.info(f"Planner created {len(tasks)} thematic research tasks")
        
        return state
    except Exception as e:
        logger.exception("Error running planner node")
        raise e