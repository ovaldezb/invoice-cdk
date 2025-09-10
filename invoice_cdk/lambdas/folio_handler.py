from pymongo import MongoClient
import json
import os
from models.folio import Folio

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
folio_collection = db["folios"]

headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    try:
        if http_method == "GET":
            if path_parameters:
                sucursal = path_parameters.get("sucursal")
                folio = folio_collection.find_one({"sucursal": sucursal})
                folio["_id"] = str(folio["_id"]) 
                if folio:
                    return {
                        "statusCode": 200,
                        "headers": headers,
                        "body": json.dumps(folio)
                    }
                else:
                    return {
                        "statusCode": 404,
                        "headers": headers,
                        "body": json.dumps({"error": "Folio not found"})
                    }
        elif http_method == "POST":
            folio = Folio(**json.loads(body))
            new_folio = folio_collection.insert_one(folio.dict()).inserted_id
            print(f"New folio created with ID: {str(new_folio)}")
            return {
                "statusCode": 201,
                "headers": headers,
                "body": json.dumps({"id_folio": str(new_folio)})
            }
        elif http_method == "PUT":
            sucursal = path_parameters.get("sucursal")
            folio = folio_collection.find_one({"sucursal": sucursal})
            folio["noFolio"] += 1
            folio_collection.update_one({"sucursal": sucursal}, {"$set": folio})
            folio_updated = folio_collection.find_one({"sucursal": sucursal})
            folio_updated["_id"] = str(folio_updated["_id"])
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(folio_updated)
            }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }