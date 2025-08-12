from bson.objectid import ObjectId
from sucursal import Sucursal

def get_sucursal_by_id(sucursal_id: str, sucursal_collection):
    return sucursal_collection.find_one({"_id": ObjectId(sucursal_id)})

def add_sucursal(sucursal: Sucursal, sucursal_collection):
    print('Adding new sucursal:', sucursal.dict())
    return sucursal_collection.insert_one(sucursal.dict()).inserted_id

def update_sucursal(sucursal_id: str, updated_data: dict, sucursal_collection):
    return sucursal_collection.update_one(
        {"_id": ObjectId(sucursal_id)}, {"$set": updated_data}
    )

def delete_sucursal(sucursal_id: str, sucursal_collection):
    return sucursal_collection.delete_one({"_id": ObjectId(sucursal_id)})