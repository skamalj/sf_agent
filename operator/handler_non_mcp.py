# handler_non_mcp.py
import json
from tools import tool_list
from utils import get_profile_id, get_all_userids_and_channels
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph_dynamodb_checkpoint import DynamoDBSaver
import boto3
from langchain_core.messages import HumanMessage
from graph_shared import build_gw_model_fn, should_continue, PrunableMessagesState

tool_node = ToolNode(tools=tool_list)

def init_graph():
    with DynamoDBSaver.from_conn_info(table_name="whatsapp_checkpoint", max_write_request_units=100, max_read_request_units=100, ttl_seconds=86400) as saver:
        graph = StateGraph(PrunableMessagesState)
        graph.add_node("agent", build_gw_model_fn(tool_list))
        graph.add_node("tools", tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges("agent", should_continue, ["tools", END])
        graph.add_edge("tools", "agent")
        return graph.compile(checkpointer=saver)

app = init_graph()

def handle_message(channel_type, recipient, message):
    profile_id = get_profile_id(recipient)
    if not profile_id:
        print(f"No profile for user: {recipient}, skipping.")
        return None

    user_profiles = get_all_userids_and_channels(profile_id)
    profile_info = "\n".join([f"- UserID: {uid}, Channel: {ch}" for uid, ch in user_profiles])

    prompt = (
        f"The following user has sent a message:\n"
        f"- UserID: {recipient} ProfileID: {profile_id}\n"
        f"- Message: {message}\n"
        f"- Sent via: {channel_type}\n\n"
        f"Here are all associated user profiles:\n"
        f"{profile_info}\n\n"
        f"Respond to user queries either on the originating channel or on the channel explicitly specified in the request, with help of comms-agent"
    )

    input_message = {"messages": [HumanMessage(prompt)]}
    config = {"configurable": {"thread_id": profile_id}}

    response = app.invoke(input_message, config)
    print("Response from agent:", response)
    agent_response = response["messages"][-1].content
    parsed_response = json.loads(agent_response)

    return {
        "fromagent": "sf-agent",
        "nextagent": parsed_response.get("nextagent", ""),
        "message": parsed_response.get("message", ""),
        "thread_id": profile_id,
        "channel_type": channel_type,
        "from": recipient
    }
