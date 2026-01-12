import os
import hashlib
from langchain_core.messages import ToolMessage

from typing import Annotated
from langchain.agents import AgentState
from typing_extensions import NotRequired
from typing import Dict

from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from core.config import settings
from core.logging import get_logger

logger = get_logger()

BASE_FILE_DIR = settings.AGENT_FILE_BASE_DIR


class DeepAgentState(AgentState):
    """
    Shared state for all agents (orchestrator, researcher, editor).

    Inherits from LangChain's AgentState and adds:
    - user_id:    separate users
    - thread_id:  separate conversations per user
    - tool_budgets:  budget for each tool

    Files are stored on REAL disk, not in state.
    """
    user_id: NotRequired[str]
    thread_id: NotRequired[str]
    tool_budgets: NotRequired[Dict[str, int]]



def _thread_folder(state: DeepAgentState) -> str:
    """Return the folder for this user/thread, create if missing."""
    user = state.get("user_id") or "default_user"
    thread = state.get("thread_id") or "default_thread"
    folder = os.path.join(BASE_FILE_DIR, user, thread)
    os.makedirs(folder, exist_ok=True)
    logger.info(f"Created folder: {folder}")
    return folder

def generate_hash(text: str, length: int = 6) -> str:
    """Generate a short hash from text for unique file naming."""
    return hashlib.md5(text.encode()).hexdigest()[:length]


def _disk_path(state: DeepAgentState, file_path: str) -> str:
    """
    Build real filesystem path as:
        agent_files/<user_id>/<thread_id>/<file_path>
    """
    folder = _thread_folder(state)
    safe_path = file_path.lstrip("/\\")
    full = os.path.join(folder, safe_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    logger.info(f"Created folder: {full}")
    return full



@tool(parse_docstring=True)
def ls(
    state: Annotated[DeepAgentState, InjectedState],
    path: str = ""
) -> list[str]:
    """
    List available files for this user/thread on the real filesystem.

    Args:
        state: Injected agent state providing user_id/thread_id.
        path: Optional subdirectory path (e.g., "researcher").
              If empty, lists root thread folder.

    Returns:
        A sorted list of filenames in the specified folder.
    """
    folder = _thread_folder(state)
    if path:
        # Join with the subdirectory path, removing leading slashes
        folder = os.path.join(folder, path.lstrip("/\\"))
    if not os.path.exists(folder):
        return []
    return sorted(os.listdir(folder))


@tool(parse_docstring=True)
def read_file(
    file_path: str,
    state: Annotated[DeepAgentState, InjectedState],
    offset: int = 0,
    limit: int = 2000,
) -> str:
    """
    Read a file from the real filesystem.

    Args:
        file_path: Relative file path under this user/thread folder.
        state: Injected agent state providing user_id/thread_id.
        offset: Line number to start from (0-based).
        limit: Maximum number of lines to return.

    Returns:
        File content with line numbers, or an error message.
    """
    path = _disk_path(state, file_path)

    if not os.path.exists(path):
        logger.error(f"File '{file_path}' does not exist.")
        return f"Error: File '{file_path}' does not exist."

    logger.info(f"Reading file: {path}")
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()

    end = min(offset + limit, len(lines))
    numbered = [
        f"{i + 1:5d}  {line}"
        for i, line in enumerate(lines[offset:end])
    ]
    return "\n".join(numbered)


@tool(parse_docstring=True)
def write_file(
    file_path: str,
    content: str,
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Write content to a file on the real filesystem.

    Args:
        file_path: Relative path (e.g., "plan.md", "notes/sources.txt").
        content: Text content to write (overwrites existing file).
        state: Injected agent state providing user_id/thread_id.
        tool_call_id: Tool call ID used to attach a ToolMessage.

    Side effects:
        - Overwrites the file on disk for this user/thread.

    Returns:
        Command that adds a ToolMessage confirming the write.
    """
    logger.debug(
        "write_file called",
        extra={
            "file_path": file_path,
            "thread_id": state.get("thread_id"),
            "user_id": state.get("user_id"),
        },
    )
    try:
        path = _disk_path(state, file_path)

        logger.info(f"Writing file: {path}")
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

        msg = f"[FILE WRITTEN] {file_path} -> {path}"
        logger.info(msg)
        return Command(
            update={
                "messages": [ToolMessage(msg, tool_call_id=tool_call_id)]
            }
        )
    except Exception as e:
        logger.exception(
            "write_file FAILED",
            extra={
                "file_path": file_path,
                "thread_id": state.get("thread_id"),
                "user_id": state.get("user_id"),
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        raise


@tool(parse_docstring=True)
def cleanup_files(
    state: Annotated[DeepAgentState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """
    Delete ALL files for this user/thread from the real filesystem.

    IMPORTANT:
    - This is a destructive operation.
    - Use ONLY when the human user explicitly asks to wipe, reset,
      or clean the workspace for this conversation.

    Args:
        state: Injected agent state with user_id/thread_id.
        tool_call_id: Tool call ID for attaching a ToolMessage.

    Behavior:
        - Looks in: agent_files/<user>/<thread>/
        - Deletes all regular files in that folder (does not recurse).

    Returns:
        Command with a ToolMessage summarizing what was deleted.
    """
    folder = _thread_folder(state)

    if not os.path.exists(folder):
        msg = "[CLEANUP] No folder found, nothing to delete."
        logger.info(msg)
        return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})

    deleted = []
    for name in os.listdir(folder):
        full = os.path.join(folder, name)
        if os.path.isfile(full):
            try:
                logger.info(f"Deleting file: {full}")
                os.remove(full)
                deleted.append(name)
            except Exception as e:
                logger.exception(f"Failed to delete file: {full}")
                deleted.append(f"{name} (error: {str(e)})")

    if not deleted:
        msg = "[CLEANUP] No files to delete."
        logger.info(msg)
    else:
        msg = f"[CLEANUP] Deleted files: {deleted}"
        logger.info(msg)

    return Command(update={"messages": [ToolMessage(msg, tool_call_id=tool_call_id)]})
