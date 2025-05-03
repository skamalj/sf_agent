
# Salesforce Integration Agent

## Overview
This project implements a serverless Salesforce integration agent using AWS Lambda, Step Functions, and various AWS services. The agent handles communication between different channels (like WhatsApp) and Salesforce, managing user profiles and executing Salesforce operations.

## Prerequisites

### AWS Services
- AWS Account with appropriate permissions
- AWS SAM CLI installed
- Python 3.10
- AWS Secrets Manager configured
- DynamoDB tables set up
- AWS SES configured (if email functionality is needed)

### Required DynamoDB Tables
1. `whatsapp_checkpoint` - For storing conversation checkpoints
2. `UserProfiles` - For storing user profile information
3. `salesforce_tokens` - For storing Salesforce OAuth tokens

### Environment Variables
The following environment variables need to be configured:

#### Direct Environment Variables (set in template.yaml)
```yaml
SALESFORCE_DOMAIN: 
SALESFORCE_REDIRECT_URI: "https://[your-api-gateway-url]/Prod/callback/"
SF_DDB_TABLE: "salesforce_tokens"
SF_API_VERSION: "v60.0"
MODEL_NAME: "gpt-4"
PROVIDER_NAME: "openai"
MSG_HISTORY_TO_KEEP: 20
DELETE_TRIGGER_COUNT: 30
```

#### Secrets Manager Variables
The following secrets need to be configured in AWS Secrets Manager:

1. `sf_client_id` - Salesforce Client ID
2. `WhatsAppAPIToken` - WhatsApp API access token
3. `WhatsappNumberID` - WhatsApp business account number ID
4. `ApiGWKey` - API Gateway key
5. `ApiGWEndpoint` - API Gateway endpoint

### Environment Variables Explanation

| Variable | Purpose |
|----------|----------|
| SALESFORCE_DOMAIN | Your Salesforce instance domain |
| SALESFORCE_REDIRECT_URI | OAuth callback URL for Salesforce authentication |
| SF_DDB_TABLE | DynamoDB table name for storing Salesforce tokens |
| SF_API_VERSION | Salesforce API version to use |
| MODEL_NAME | LLM model name for agent responses |
| PROVIDER_NAME | LLM provider name |
| MSG_HISTORY_TO_KEEP | Minimum number of messages to keep in history |
| DELETE_TRIGGER_COUNT | Maximum message count before pruning |

## Installation and Deployment


### Deployment

1. Build the SAM application:
bash
sam build


2. Deploy using SAM:
bash
sam deploy --guided


During the guided deployment, you'll need to provide:
- Stack name
- AWS Region
- Parameter values for secret names
- Confirm changes before deployment

