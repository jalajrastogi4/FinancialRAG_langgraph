import sqlite3
import os
from pathlib import Path
from langgraph.checkpoint.sqlite import SqliteSaver

from core.logging import get_logger

logger = get_logger()


def get_checkpointer():
    """
    Initialize and return a SQLite checkpointer for LangGraph state persistence.
    
    Returns:
        SqliteSaver: Configured checkpointer instance
        
    Raises:
        RuntimeError: If checkpoint initialization fails
    """

    db_path = "data/deep_finance_langgraph.db"

    try:
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured checkpoint directory exists: {db_dir}")

        logger.info(f"Initializing checkpoint database at: {db_path}")
        conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
        )

        checkpointer = SqliteSaver(conn=conn)
        logger.info("Checkpoint database initialized successfully")

        return checkpointer
    
    except sqlite3.OperationalError as e:
        logger.exception("SQLite operational error during checkpoint initialization")
        raise RuntimeError(
            f"Failed to initialize checkpoint database at {db_path}. "
            f"Error: {e}. Check file permissions and disk space."
        ) from e

    except Exception as e:
        logger.exception("Unexpected error during checkpoint initialization")
        raise RuntimeError(
            f"Failed to initialize checkpoint database: {e}"
        ) from e