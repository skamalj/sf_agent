# handler_mcp.py
import json
import os
from utils import get_profile_id, get_all_userids_and_channels
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
from langgraph_dynamodb_checkpoint import DynamoDBSaver
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from langchain_mcp_adapters.tools import load_mcp_tools
from graph_shared import build_gw_model_fn, should_continue, PrunableMessagesState

async def handle_message_mcp(channel_type, recipient, message):
    mcp_server_url = os.environ.get("MCP_SERVER_URL")
    if not mcp_server_url:
        print("MCP_SERVER_URL environment variable is not set. Exiting.")
        return None

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

    async with streamablehttp_client(mcp_server_url) as (read, write, _):
        async with ClientSession(read, write) as client:
            await client.initialize()
            mcp_tools = await load_mcp_tools(client)

            graph = StateGraph(PrunableMessagesState)
            graph.add_node("agent", build_gw_model_fn(mcp_tools))
            graph.add_node("tools", ToolNode(tools=mcp_tools))
            graph.add_edge(START, "agent")
            graph.add_conditional_edges("agent", should_continue, ["tools", END])
            graph.add_edge("tools", "agent")

            with DynamoDBSaver.from_conn_info(table_name="whatsapp_checkpoint", max_write_request_units=100, max_read_request_units=100, ttl_seconds=86400) as saver:
                dynamic_app = graph.compile(checkpointer=saver)
                response = await dynamic_app.ainvoke(input_message, config)

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
