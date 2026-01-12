def extract_text_from_message(msg) -> str:
    """
    Normalize AIMessage content across providers (Gemini/OpenAI/etc).
    """
    content = msg.content

    # Case 1: Plain string
    if isinstance(content, str):
        return content

    # Case 2: Gemini-style content blocks (list of dicts)
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(part.get("text", ""))
        return "\n".join(parts)

    # Fallback
    return ""