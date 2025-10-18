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
            Constants.STATUS_CODE: 200,
            Constants.BODY: json.dumps({"environment": ENV}),
            Constants.HEADERS_KEY: headers
        }
    else:
        return {
            Constants.STATUS_CODE: 405,
            Constants.BODY: json.dumps({"error": "Method Not Allowed"}),
            Constants.HEADERS_KEY: headers
        }

