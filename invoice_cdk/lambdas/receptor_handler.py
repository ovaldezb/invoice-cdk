import json
import os
from db_receptor import guarda_receptor, obtiene_receptor_by_rfc
from receptor import Receptor
from pymongo import MongoClient
from bson import json_util
from http import HTTPStatus

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
receptor_collection = db["receptors"]

headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    if http_method == "POST":
        # Create a new receptor
        receptor = Receptor(**json.loads(body))
        receptor_id = guarda_receptor(receptor, receptor_collection)
        return {
            "statusCode": HTTPStatus.CREATED,
            "headers": headers,
            "body": json_util.dumps({"id": str(receptor_id)})
        }
    elif http_method == "GET" and path_parameters:
        # Get a receptor by ID
        receptor_id = path_parameters.get("id_receptor")
        receptor = obtiene_receptor_by_rfc(receptor_id, receptor_collection)
        if receptor:
            receptor["_id"] = str(receptor["_id"])
            return {
                "statusCode": HTTPStatus.OK,
                "headers": headers,
                "body": json_util.dumps(receptor)
            }
        else:
            return {
                "statusCode": HTTPStatus.NOT_FOUND,
                "headers": headers,
                "body": json_util.dumps({"error": "Receptor not found"})
            }
    else:
        return {
            "statusCode": HTTPStatus.BAD_REQUEST,
            "headers": headers,
            "body": json_util.dumps({"error": "Invalid request"})
        }