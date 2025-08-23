import os
import json
import requests

SW_USER_NAME = os.getenv("SW_USER_NAME")
SW_USER_PASSWORD = os.getenv("SW_USER_PASSWORD")
SW_URL = os.getenv("SW_URL")

headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    try:
        http_method = event["httpMethod"]
        path_parameters = event.get("pathParameters")
        body = event.get("body")
        print(f"Received body: {body}")
        if http_method == "POST":
            # Handle POST request
            sw_token = requests.post(
                f"{SW_URL}/security/authenticate",
                auth=(SW_USER_NAME, SW_USER_PASSWORD)
            ).json()
            print(f"SW Token: {sw_token}")
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({"token": sw_token})
            }

    except Exception as e:
        print(f"Error: {str(e)}")