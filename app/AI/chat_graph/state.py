from langchain_core.messages import AnyMessage
from typing import Annotated, TypedDict, List
from langgraph.graph.message import add_messages

class State(TypedDict):
    chat_id: int
    user_question: str
    file: str
    messages: Annotated[List[AnyMessage], add_messages]