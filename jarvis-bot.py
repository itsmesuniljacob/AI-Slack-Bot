import os
import json
import urllib.request

# Isolate the event body from the event package
def isolate_event_body(event):
    # Dump the event to a string, then load it as a dict
    event_string = json.dumps(event, indent=2)
    event_dict = json.loads(event_string)

    # Isolate the event body from event package
    event_body = event_dict["body"]
    body = json.loads(event_body)

    # Return the event
    return body


def lambda_handler(event, context):
    """
    Orchestrator Lambda to process Slack message events asynchronously
    and send a reply back to Slack.
    """
    print("Received event:", json.dumps(event))

    slack_event = event.get("event", {})

    # 1. Ignore messages from bots (including yourself)
    if "bot_id" in slack_event:
        print("Message is from a bot. Ignoring to avoid loop.")
        return {"status": "ignored bot message"}

    event_body=isolate_event_body(event)

    print("Event body:", event_body)

    # Extract channel & text from event (adjust based on your payload structure)
    channel_id = event_body["event"]["channel"]
    user_message = event_body["event"]["text"]

    if not channel_id:
        print("No channel found in event.")
        return {"status": "error", "reason": "missing channel"}

    # Prepare reply text
    reply_text = f"Hello! You said: {user_message}"

    # Send message back to Slack
    send_slack_message(channel_id, reply_text)

    return {"status": "message sent"}


def send_slack_message(channel, text):
    """
    Sends a message to Slack using the Web API.
    Requires SLACK_BOT_TOKEN in environment variables.
    """
    slack_token = os.environ["SLACK_BOT_TOKEN"]
    slack_url = "https://slack.com/api/chat.postMessage"

    payload = {
        "channel": channel,
        "text": text
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(slack_url, data=data)
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {slack_token}")

    try:
        with urllib.request.urlopen(req) as resp:
            resp_body = resp.read().decode("utf-8")
            print(f"Slack response: {resp_body}")
            return json.loads(resp_body)
    except Exception as e:
        print(f"Error sending message to Slack: {e}")
        raise