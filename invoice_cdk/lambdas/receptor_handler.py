import json
import os
from dbaccess.db_receptor import (
    guarda_receptor, 
    obtiene_receptor_by_rfc,
    update_receptor
    )
from models.receptor import Receptor
from pymongo import MongoClient
from bson import json_util
from http import HTTPStatus
from utils import valida_cors
from constantes import Constants

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
receptor_collection = db["receptors"]

headers = Constants.HEADERS.copy()

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    if http_method == Constants.POST:
        # Create a new receptor
        receptor = Receptor(**json.loads(body))
        receptor_id = guarda_receptor(receptor, receptor_collection)
        return {
            Constants.STATUS_CODE: HTTPStatus.CREATED,
            Constants.HEADERS_KEY: headers,
            Constants.BODY: json_util.dumps({"id": str(receptor_id)})
        }
    elif http_method == Constants.GET and path_parameters:
        # Get a receptor by ID
        receptor_id = path_parameters.get("id_receptor")
        receptor = obtiene_receptor_by_rfc(receptor_id, receptor_collection)
        if receptor:
            receptor["_id"] = str(receptor["_id"])
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json_util.dumps(receptor)
            }
        else:
            return {
                Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json_util.dumps({"error": "Receptor not found"})
            }
    elif http_method == Constants.PUT:
        # Update a receptor by ID
        receptor_id = path_parameters.get("id_receptor")
        receptor_data = json.loads(body)
        update_result = update_receptor(receptor_id, receptor_data, receptor_collection)
        
        if update_result.matched_count > 0:
            # Get the updated receptor to return it
            updated_receptor = obtiene_receptor_by_rfc(receptor_id, receptor_collection)
            if updated_receptor:
                updated_receptor["_id"] = str(updated_receptor["_id"])
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json_util.dumps({"message": "Receptor updated", "receptor": updated_receptor})
            }
        else:
            return {
                Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json_util.dumps({"error": "Receptor not found"})
            }

    else:
        return {
            Constants.STATUS_CODE: HTTPStatus.BAD_REQUEST,
            Constants.HEADERS_KEY: headers,
            Constants.BODY: json_util.dumps({"error": "Invalid request"})
        }