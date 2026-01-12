from core.logging import get_logger

logger = get_logger()


class ToolBudgetExceeded(Exception):
    """Raised when a tool budget is exhausted."""

def enforce_budget(state, tool_name: str):
    budgets = state.get("tool_budgets", {})

    if tool_name not in budgets:
        # No budget defined = unlimited
        return

    if budgets[tool_name] <= 0:
        logger.warning(f"Tool budget exceeded: {tool_name}")
        raise ToolBudgetExceeded(f"Tool budget exceeded for {tool_name}")

    budgets[tool_name] -= 1
    logger.debug(f"Tool budget remaining for {tool_name}: {budgets[tool_name]}")