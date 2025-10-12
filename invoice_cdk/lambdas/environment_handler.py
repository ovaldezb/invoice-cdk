import json
import os
from constantes import Constants
from utils import valida_cors

ENV = os.environ.get("ENV")
headers = Constants.HEADERS.copy()

def handler(event, context):
    http_method = event["httpMethod"]
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    if http_method == "GET":
        return {
            "statusCode": 200,
            "body": json.dumps({"environment": ENV}),
            "headers": headers
        }
    else:
        return {
            "statusCode": 405,
            "body": "Method Not Allowed",
            "headers": headers
        }

