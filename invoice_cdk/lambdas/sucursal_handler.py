import json
import os
from pymongo import MongoClient
from http import HTTPStatus
from db_sucursal import (
    add_sucursal,
    update_sucursal,
    delete_sucursal,
)
from sucursal import Sucursal
headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
sucursal_collection = db["sucursales"]

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    
    try:
        if http_method == "POST":
            sucursal_data = json.loads(body)
            sucursal = Sucursal(**sucursal_data)
            sucursal_id = add_sucursal(sucursal, sucursal_collection)
            return {
                "statusCode": HTTPStatus.CREATED,
                "body": json.dumps({"message": "Sucursal added", "id": str(sucursal_id)}),
                "headers": headers
            }

        elif http_method == "PUT":
            sucursal_id = path_parameters["id"]
            updated_data = json.loads(body)
            update_sucursal(sucursal_id, updated_data, sucursal_collection)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Sucursal updated"}),
                "headers": headers
            }

        elif http_method == "DELETE":
            sucursal_id = path_parameters["id"]
            delete_sucursal(sucursal_id, sucursal_collection)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "Sucursal deleted"}),
                "headers": headers
            }

    except Exception as e:
        print(f"Error processing request: {e}")
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "body": json.dumps({"error": str(e)}),
            "headers": headers
        }