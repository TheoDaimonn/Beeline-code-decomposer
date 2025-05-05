"""Utility & helper functions."""

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai.chat_models import ChatOpenAI
import os
from dotenv import load_dotenv
load_dotenv(override=True)

def get_message_text(msg: BaseMessage) -> str:
    """Get the text content of a message."""
    content = msg.content
    if isinstance(content, str):
        return content
    elif isinstance(content, dict):
        return content.get("text", "")
    else:
        txts = [c if isinstance(c, str) else (c.get("text") or "") for c in content]
        return "".join(txts).strip()


def load_chat_model(fully_specified_name: str) -> BaseChatModel:
    """Load a chat model from a fully specified name.

    Args:
        fully_specified_name (str): String in the format 'model/tag'.
    """
    llm = ChatOpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ["OPENAI_BASE_URL"],
        temperature=0.1,
    )
    return llm


