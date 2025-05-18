# graph_shared.py
import os
from langchain_core.messages import SystemMessage
from langgraph_utils import call_model, create_tools_json
from langgraph_reducer import PrunableStateFactory

model_name = os.getenv("MODEL_NAME")
provider_name = os.getenv("PROVIDER_NAME")

min_keep = int(os.getenv("MSG_HISTORY_TO_KEEP", 20))
max_keep = int(os.getenv("DELETE_TRIGGER_COUNT", 30))

PrunableMessagesState = PrunableStateFactory.create_prunable_state(min_keep, max_keep)

def should_continue(state) -> str:
    last_message = state['messages'][-1]
    return "tools" if last_message.tool_calls else "END"

def build_gw_model_fn(dynamic_tools):
    def call_gw_model(state):
        with open("agent_prompt.txt", "r", encoding="utf-8") as file:
            system_message = file.read()

        messages = state["messages"]
        messages.insert(0, SystemMessage(content=system_message))

        json_tools = create_tools_json(dynamic_tools)
        response = call_model(model_name, provider_name, messages, json_tools)
        return {"messages": [response]}

    return call_gw_model
