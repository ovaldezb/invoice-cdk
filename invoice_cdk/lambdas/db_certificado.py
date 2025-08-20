from bson.objectid import ObjectId
from certificate import Certificado


def add_certificate(certificate: Certificado, certificates_collection) -> str:
    return certificates_collection.insert_one(certificate.dict()).inserted_id

def update_certificate(cert_id: str, updated_data: dict, certificates_collection):
    return certificates_collection.update_one(
        {"_id": ObjectId(cert_id)}, {"$set": updated_data}
    )

def list_certificates(certificates_collection):
    return list(certificates_collection.find())

def get_certificate_by_id(cert_id: str, certificates_collection):
    return certificates_collection.find_one({"_id": ObjectId(cert_id)})

def delete_certificate(cert_id: str, certificates_collection):
    return certificates_collection.delete_one({"_id": ObjectId(cert_id)})
