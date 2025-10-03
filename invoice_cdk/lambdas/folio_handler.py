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
    except Exception as e:
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.BODY: json.dumps({"error": str(e)}),
            Constants.HEADERS_KEY: headers
        }