import os
import urllib.parse
import requests
from langchain_core.tools import tool
from utils import get_secret
import boto3
import json

@tool
def generate_salesforce_oauth_url(profile_id: str) -> str:
    """
    Generates a Salesforce OAuth2 authorization URL using values from environment variables
    and a provided profile_id.
    
    Env Variables:
    - SALESFORCE_DOMAIN
    - SALESFORCE_CLIENT_ID
    - SALESFORCE_REDIRECT_URI
    
    Args:
        profile_id (str): The user profile ID to be passed in the state parameter.
    
    Returns:
        str: Complete Salesforce OAuth2 URL.
    """
    domain = os.environ.get("SALESFORCE_DOMAIN")
    client_id = os.environ.get("SALESFORCE_CLIENT_ID")
    redirect_uri = os.environ.get("SALESFORCE_REDIRECT_URI")

    if not all([domain, client_id, redirect_uri]):
        raise ValueError("Missing required environment variables.")

    base_url = f"https://{domain}/services/oauth2/authorize"
    query_params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": "api",
        "state": f"profile:{profile_id}"
    }

    return f"{base_url}?{urllib.parse.urlencode(query_params)}"


@tool
def execute_salesforce_soql(soql_query: str, profile_id: str) -> list[dict]:
    """
    Executes a SOQL query against Salesforce using credentials fetched from DynamoDB.

    Args:
        soql_query (str): The SOQL query to execute.
        profile_id (str): The wa_id used to look up Salesforce credentials in DynamoDB.

    DynamoDB Table Schema (per item):
        - wa_id (str): Primary key
        - access_token (str)
        - instance_url (str)
        - refresh_token (str, optional)
        - issued_at (int, optional)

    Required environment variables:
        - SF_DDB_TABLE: Name of the DynamoDB table
        - SF_API_VERSION: Optional, defaults to 'v60.0'

    Returns:
        List[dict]: Records from the query result.

    Raises:
        Exception: If credentials are missing or query fails.
    """
    table_name = os.getenv("SF_DDB_TABLE")
    api_version = os.getenv("SF_API_VERSION", "v60.0")

    if not table_name:
        raise EnvironmentError("Missing SF_DDB_TABLE in environment variables.")

    # Fetch credentials from DynamoDB
    ddb = boto3.resource("dynamodb")
    table = ddb.Table(table_name)

    response = table.get_item(Key={"wa_id": profile_id})
    if "Item" not in response:
        raise Exception(f"No record found in DynamoDB for wa_id: {profile_id}")

    item = response["Item"]
    access_token = item.get("access_token")
    instance_url = item.get("instance_url")

    if not access_token or not instance_url:
        raise Exception(f"Missing access_token or instance_url for wa_id: {profile_id}")

    # Execute SOQL query
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    url = f"{instance_url}/services/data/{api_version}/query"
    params = {"q": soql_query}

    resp = requests.get(url, headers=headers, params=params)

    if resp.status_code != 200:
        raise Exception(f"Salesforce query failed: {resp.status_code} - {resp.text}")

    return resp.json().get("records", [])

   
@tool
def send_whatsapp_message(recipient, message):
    """
    Sends a WhatsApp message using the Meta API.

    :param recipient: The recipient's phone number.
    :return: The JSON response from the API call.
    """
    access_token = get_secret("WhatsAppAPIToken")  # Fetch token from Secrets Manager
    whatsapp_number_id = get_secret("WhatsappNumberID")  # Fetch WhatsApp number ID from Secrets Manager
    if not access_token:
        print("Failed to retrieve access token.")
        return None
    
    url = f"https://graph.facebook.com/v22.0/{whatsapp_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"body": message}
    }
    
    response = requests.post(url, headers=headers, json=payload)
    return response.json()


@tool
def send_email_via_ses(email_json: str):
    """
    Sends an email using AWS SES.

    Expected JSON format:
    {
        "to_email": "recipient@example.com",
        "subject": "Subject Line",
        "body": "Email body content",
        "is_html": false  # Set to true to enable HTML formatting for a better-looking report
    }

    Note:
    For visually appealing, well-formatted reports (e.g., tables, styled text), set "is_html" to true and use HTML in the "body".

    :param email_json: JSON string containing email details.
    :return: Response message indicating success or failure.
    """
    try:
        # Parse JSON input
        email_data = json.loads(email_json)
        to_email = email_data.get("to_email")
        subject = email_data.get("subject", "No Subject")
        body = email_data.get("body", "")
        is_html = email_data.get("is_html", False)

        # Ensure required fields are present
        if not to_email or not body:
            return "Error: Missing required fields ('to_email' or 'body')."

        # Construct email body (HTML or plain text)
        message_body = {"Html": {"Data": body}} if is_html else {"Text": {"Data": body}}
        ses_client = boto3.client("ses")
        FROM_EMAIL = os.getenv("EMAIL_FROM", "agent@mockify.com")
        # Send email via AWS SES
        response = ses_client.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": message_body,
            },
        )
        return f"Email sent successfully! Message ID: {response['MessageId']}"

    except Exception as e:
        return f"Error sending email: {str(e)}"


tool_list = [generate_salesforce_oauth_url, execute_salesforce_soql, send_email_via_ses, send_whatsapp_message]
