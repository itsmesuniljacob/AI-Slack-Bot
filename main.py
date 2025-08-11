import json
import base64
from urllib.parse import unquote_plus
import os
import boto3

def lambda_handler(event, context):
    # print(json.dumps(event))
    message = (base64.b64decode(event['body']).decode('utf-8').split('text=')[1]).split('&')[0]
    body = base64.b64decode(event['body']).decode('utf-8')
    print("Body: " + body)
    print("Message: " + unquote_plus(message))
    
    lambda_client = boto3.client('lambda')

    try:

        response = lambda_client.invoke(
            FunctionName=os.environ['PROCESSOR_FUNCTION_NAME'],
            InvocationType='Event',
            Payload=json.dumps(event)
        )
        
        print(f"Processor triggered, status code: {response['StatusCode']}")
        
        # print(json.loads(response['Payload'].read().decode('utf-8')))
        # Handle Slack URL verification challenge
        if 'challenge' in body:
            
            return {
                'statusCode': 200,
                'body': body.split('challenge=')[1].split('&')[0]
            }

        return {
            'statusCode': 200,
            'body': json.dumps('Hello from Lambda!')
        }


    except Exception as e:
        print(f"Error: {type(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('Error!')
        }
