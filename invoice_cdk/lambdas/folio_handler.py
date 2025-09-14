from http import HTTPStatus
from constantes import Constants
from receptor_handler import valida_cors
from pymongo import MongoClient
import json
import os
from models.folio import Folio

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
folio_collection = db["folios"]

headers = Constants.HEADERS.copy()

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    try:
        if http_method == Constants.GET:
            if path_parameters:
                sucursal = path_parameters.get("sucursal")
                folio = folio_collection.find_one({"sucursal": sucursal})
                folio["_id"] = str(folio["_id"]) 
                if folio:
                    return {
                        Constants.STATUS_CODE: HTTPStatus.OK,
                        Constants.HEADERS_KEY: headers,
                        Constants.BODY: json.dumps(folio)
                    }
                else:
                    return {
                        Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                        Constants.HEADERS_KEY: headers,
                        Constants.BODY: json.dumps({"error": "Folio not found"})
                    }
        elif http_method == Constants.POST:
            folio = Folio(**json.loads(body))
            new_folio = folio_collection.insert_one(folio.dict()).inserted_id
            print(f"New folio created with ID: {str(new_folio)}")
            return {
                Constants.STATUS_CODE: HTTPStatus.CREATED,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({"id_folio": str(new_folio)})
            }
        elif http_method == Constants.PUT:
            sucursal = path_parameters.get("sucursal")
            folio = folio_collection.find_one({"sucursal": sucursal})
            folio["noFolio"] += 1
            folio_collection.update_one({"sucursal": sucursal}, {"$set": folio})
            folio_updated = folio_collection.find_one({"sucursal": sucursal})
            folio_updated["_id"] = str(folio_updated["_id"])
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps(folio_updated)
            }
    except Exception as e:
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.BODY: json.dumps({"error": str(e)}),
            Constants.HEADERS_KEY: headers
        }