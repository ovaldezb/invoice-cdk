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

headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    try:
        http_method = event["httpMethod"]
        if http_method == "GET":
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
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "uso_cfdi": uso_cfdi,
                    "regimen_fiscal": regimen_fiscal,
                    "forma_pago": forma_pago
                })
            }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": headers,
            "body": json.dumps({
                "error": str(e)
            })
        }