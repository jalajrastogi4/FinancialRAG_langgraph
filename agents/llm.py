from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import settings
from core.observability import get_langfuse_handler
from core.logging import get_logger

logger = get_logger()


def get_llm():
    """
    Create and return a configured LLM instance.
    """
    callbacks = []

    try:
        handler = get_langfuse_handler()
        if handler:
            callbacks.append(handler)
            logger.debug("Langfuse callback attached to LLM")
    except Exception as e:
        logger.warning("Failed to attach Langfuse handler", extra={"error": str(e)})

    try:
        logger.info("Initializing LLM")
        llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            api_key=settings.GOOGLE_API_KEY,
            callbacks=callbacks,
        )
        logger.info("Initialized LLM")

        return llm
    except Exception as e:
        logger.exception("Failed to initialize LLM")
        raise