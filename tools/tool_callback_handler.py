from langchain_core.callbacks.base import BaseCallbackHandler
from core.logging import get_logger

logger = get_logger()


class ToolErrorLogger(BaseCallbackHandler):
    def __init__(self):
        self._current_tool = None
        self._current_tool_input = None

    def on_tool_start(self, serialized, input_str, **kwargs):
        # serialized["name"] contains the tool name
        self._current_tool = serialized.get("name")
        self._current_tool_input = input_str

    def on_tool_error(self, error, **kwargs):
        logger.exception(
            f"TOOL ERROR in {self._current_tool}",
            extra={
                "tool_name": self._current_tool,
                "tool_input": self._current_tool_input,
                "error_type": type(error).__name__,
                "error": str(error),
            },
        )

        # Clear state to avoid leakage
        self._current_tool = None
        self._current_tool_input = None
