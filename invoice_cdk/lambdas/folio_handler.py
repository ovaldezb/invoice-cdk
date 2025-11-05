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
    body = event.get("body")
    path_parameters = event.get("pathParameters")
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    try:
        if http_method == Constants.POST:
            folio = Folio(**json.loads(body))
            existing_folio = folio_collection.find_one({"sucursal":folio.sucursal})
            if existing_folio:
                return {
                    Constants.STATUS_CODE: HTTPStatus.ACCEPTED,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({"mensaje": "Folio already exists"})
                }
            new_folio = folio_collection.insert_one(folio.dict()).inserted_id
            return {
                Constants.STATUS_CODE: HTTPStatus.CREATED,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({"id_folio": str(new_folio)})
            }
        elif http_method == Constants.PUT:
            data = json.loads(body)
            sucursal = data["codigo_sucursal"]
            folio = data["folio"]
            result = folio_collection.update_one({"sucursal": sucursal}, {"$set": {"noFolio": folio}})

            if result.matched_count == 0:
                return {
                    Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({"mensaje": "Folio not found"})
                }
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({"mensaje": "Folio updated"})
            }
        elif http_method == Constants.GET:
            sucursal = path_parameters.get("sucursal")
            folio_data = folio_collection.find_one({"sucursal": sucursal})
            if not folio_data:
                return {
                    Constants.STATUS_CODE: HTTPStatus.NOT_FOUND,
                    Constants.HEADERS_KEY: headers,
                    Constants.BODY: json.dumps({"mensaje": "Folio not found"})
                }
            folio_data["_id"] = str(folio_data["_id"])
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({"folio": folio_data})
            }
    except Exception as e:
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.BODY: json.dumps({"error": str(e)}),
            Constants.HEADERS_KEY: headers
        }