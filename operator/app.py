import json
import os
import boto3
import asyncio
from handler_non_mcp import handle_message
from handler_mcp import handle_message_mcp

stepfunctions = boto3.client("stepfunctions")

USE_MCP = os.getenv("USE_MCP", "n").lower() == "y"
handler = handle_message_mcp if USE_MCP else handle_message

def lambda_handler(event, context):
    print("Received event:", json.dumps(event, indent=2))

    async def process_event():
    # Handle Step Function event with task token
        if "taskToken" in event and "input" in event:
            task_token = event["taskToken"]
            input_data = event["input"]
            channel_type = input_data.get("channel_type")
            recipient = input_data.get("from")
            message = input_data.get("message")

            result = await handler(channel_type, recipient, message)
            print("Handler result:", result)
            if result:
                stepfunctions.send_task_success(
                    taskToken=task_token,
                    output=json.dumps(result)
                )
            else:
                stepfunctions.send_task_failure(
                    taskToken=task_token,
                    error="UserProfileError",
                    cause="Missing profile or invalid input."
                )
            return

        # Handle SQS event
        if "Records" in event:
            for record in event["Records"]:
                body = json.loads(record["body"])
                channel_type = body.get("channel_type")
                recipient = body.get("from")
                message = body.get("messages")

                if not all([channel_type, recipient, message]):
                    print("Skipping message due to missing fields")
                    continue

                await handler(channel_type, recipient, message)

    return asyncio.run(process_event())
