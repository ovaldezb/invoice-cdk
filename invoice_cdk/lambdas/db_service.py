from pymongo import MongoClient
from bson.objectid import ObjectId
from certificate import Certificado

import os

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
certificates_collection = db["certificates"]

def add_certificate(certificate: Certificado):
    return certificates_collection.insert_one(certificate.dict()).inserted_id

def update_certificate(cert_id: str, updated_data: dict):
    return certificates_collection.update_one(
        {"_id": ObjectId(cert_id)}, {"$set": updated_data}
    )

def list_certificates():
    return list(certificates_collection.find())

def delete_certificate(cert_id: str):
    return certificates_collection.delete_one({"_id": ObjectId(cert_id)})
