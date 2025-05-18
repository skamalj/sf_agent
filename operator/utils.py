import boto3

# Initialize AWS resources
dynamodb = boto3.resource("dynamodb", region_name="ap-south-1")  # Change region if needed
table = dynamodb.Table("UserProfiles")

def get_secret(secret_name):
    """
    Fetches the WhatsApp API token from AWS Secrets Manager.
    """
    client = boto3.client("secretsmanager")
    
    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret_data = response["SecretString"]
        return str(secret_data)
    except Exception as e:
        print(f"Error fetching secret: {e}")
        return None
    
def get_profile_id(userid):
    """Fetch profile_id from DynamoDB using GSI on userid."""
    response = table.query(
        IndexName="UserIdIndex",
        KeyConditionExpression="userid = :uid",
        ExpressionAttributeValues={":uid": userid}
    )
    items = response.get("Items", [])
    return items[0]["profile_id"] if items else None

def get_all_userids_and_channels(profile_id):
    """Fetch all userids and channels associated with the profile_id."""
    response = table.query(
        KeyConditionExpression="profile_id = :pid",
        ExpressionAttributeValues={":pid": profile_id}
    )
    items = response.get("Items", [])
    return [(item["userid"], item["channel"]) for item in items]


