from enum import Enum
from typing import Annotated, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field
from langgraph.channels import LastValue

from tools.file_tools import DeepAgentState

class PlannerDecision(str, Enum):
    DIRECT = "direct_answer"
    RESEARCH = "research"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class GraphStatus(str, Enum):
    INIT = "init"
    PLANNING = "planning"
    RESEARCHING = "researching"
    VERIFYING = "verifying"
    EDITING = "editing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchTask(TypedDict):
    theme_id: int
    question: str
    file_hash: str
    status: TaskStatus
    retries: int
    error: Optional[str]


def merge_research_tasks(
    old: List[ResearchTask],
    updates: List[ResearchTask],
) -> List[ResearchTask]:
    """
    Merge updated research tasks back into the task list by theme_id.
    """
    task_map = {t["theme_id"]: t for t in old}

    for updated in updates:
        task_map[updated["theme_id"]] = updated

    return list(task_map.values())


class GraphState(DeepAgentState, total=False):
    """
    Canonical shared state for LangGraph execution.

    Inherits:
    - messages
    - user_id
    - thread_id

    Adds:
    - planner outputs
    - task tracking
    - execution metadata
    """

    planner_decision: PlannerDecision
    thematic_questions: List[str]
    research_tasks: Annotated[List[ResearchTask], merge_research_tasks]
    # current_task: Optional[ResearchTask]
    # tool_budgets: Dict[str, int]
    graph_status: GraphStatus
    last_error: Optional[str]


class PlannerOutput(BaseModel):
    decision: PlannerDecision = Field(
        description="Whether to answer directly or run research"
    )
    thematic_questions: List[str] = Field(
        description="3-5 high-level thematic questions"
    )