from http import HTTPStatus
from constantes import Constants
from receptor_handler import valida_cors
from pymongo import MongoClient
import json
import os
from dbaccess.db_datos_factura import(
    get_uso_cfdi,
    get_regimen_fiscal,
    get_forma_pago
)

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
usocfdi_collection = db["usocfdis"]
regimen_fiscal_collection = db["regimenfiscal"]
forma_pago_collection = db["formapago"]

headers = Constants.HEADERS.copy()

def handler(event, context):
    origin = event.get("headers", {}).get("origin")
    headers["Access-Control-Allow-Origin"] = valida_cors(origin)
    try:
        http_method = event["httpMethod"]
        if http_method == Constants.GET:
            uso_cfdi = get_uso_cfdi(usocfdi_collection)
            for uso in uso_cfdi:
                uso["_id"] = str(uso["_id"])  # Convert ObjectId to string
            regimen_fiscal = get_regimen_fiscal(regimen_fiscal_collection)
            for regimen in regimen_fiscal:
                regimen["_id"] = str(regimen["_id"])  # Convert ObjectId to string
            forma_pago = get_forma_pago(forma_pago_collection)
            for forma in forma_pago:
                forma["_id"] = str(forma["_id"])  # Convert ObjectId to string
            return {
                Constants.STATUS_CODE: HTTPStatus.OK,
                Constants.HEADERS_KEY: headers,
                Constants.BODY: json.dumps({
                    "uso_cfdi": uso_cfdi,
                    "regimen_fiscal": regimen_fiscal,
                    "forma_pago": forma_pago
                })
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            Constants.STATUS_CODE: HTTPStatus.INTERNAL_SERVER_ERROR,
            Constants.HEADERS_KEY: headers,
            Constants.BODY: json.dumps({
                "error": str(e)
            })
        }