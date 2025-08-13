import os
import json
import urllib.request
import boto3

# Cache secrets after first fetch so Lambda cold start only hits Secrets Manager once
cached_secrets = None

def get_slack_secrets():
    """
    Fetch Slack secrets (bot token and bot user ID) from AWS Secrets Manager.
    Secrets should be stored as JSON:
    {
        "SLACK_BOT_TOKEN": "xoxb-123...",
        "SLACK_BOT_USER_ID": "U12345678"
    }
    """
    global cached_secrets
    if cached_secrets:
        return cached_secrets

    secret_name = os.environ["SLACK_SECRET_NAME"]
    region_name = os.environ.get("AWS_REGION", "ap-south-1")

    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_name)
        secret_string = get_secret_value_response["SecretString"]
        cached_secrets = json.loads(secret_string)
        return cached_secrets
    except Exception as e:
        print(f"Error retrieving secrets: {e}")
        raise


def isolate_event_body(event):
    """
    Extracts and returns the Slack payload from the API Gateway event wrapper.
    """
    event_string = json.dumps(event, indent=2)
    event_dict = json.loads(event_string)

    # Isolate the event body from event package
    event_body = event_dict["body"]
    body = json.loads(event_body)

    # Return the event
    return body



def lambda_handler(event, context):

    # Get Slack credentials from Secrets Manager
    secrets = get_slack_secrets()
    slack_token = secrets["SLACK_BOT_TOKEN"]
    bot_user_id = secrets["SLACK_BOT_USER_ID"]

    print("Raw event from API Gateway:", json.dumps(event))

    # Parse Slack event payload
    event_body = isolate_event_body(event)
    print("Parsed Slack event body:", json.dumps(event_body))

    slack_event = event_body.get("event", {})

    # --- Loop Protection ---
    # 1. Ignore any bot messages (bot_id present)
    if "bot_id" in slack_event:
        print("Ignoring: message is from a bot (bot_id present).")
        return {"status": "ignored bot message"}

    # 2. Ignore if sender is this bot's own user ID
    if slack_event.get("user") == bot_user_id:
        print(f"Ignoring: message from self (user_id = {bot_user_id}).")
        return {"status": "ignored self message"}
    # --- End Loop Protection ---

    # Extract channel, text, and timestamp
    channel_id = slack_event.get("channel")
    user_message = slack_event.get("text", "")
    thread_ts = slack_event.get("ts")  # Slack message timestamp for threading

    if not channel_id:
        print("No channel found in event.")
        return {"status": "error", "reason": "missing channel"}

    # Prepare reply
    reply_text = f"Hello! You said: {user_message}"

    # Send threaded reply to Slack
    send_slack_message(slack_token, channel_id, reply_text, thread_ts)

    return {"status": "message sent"}


def send_slack_message(slack_token, channel, text, thread_ts=None):
    """
    Sends a message to Slack using chat.postMessage API.
    Requires SLACK_BOT_TOKEN in Lambda environment variables.
    """
    slack_url = "https://slack.com/api/chat.postMessage"

    payload = {
        "channel": channel,
        "text": text
    }

    # Add thread timestamp if replying in a thread
    if thread_ts:
        payload["thread_ts"] = thread_ts

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(slack_url, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {slack_token}")

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            print(f"Slack API response: {resp_body}")
            return json.loads(resp_body)
    except Exception as e:
        print(f"Error sending message to Slack: {e}")
        raise
