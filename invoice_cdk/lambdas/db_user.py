from pymongo import MongoClient
from bson.objectid import ObjectId
from models.usuario import Usuario

client = MongoClient(os.getenv("MONGODB_URI"))
db = client[os.getenv("DB_NAME")]
usuarios_collection = db["usuarios"]

def add_usuario(usuario: Usuario):
    return usuarios_collection.insert_one(usuario.dict()).inserted_id

def update_usuario(user_id: str, updated_data: dict):
    return usuarios_collection.update_one(
        {"_id": ObjectId(user_id)}, {"$set": updated_data}
    )
def list_usuarios():
    return list(usuarios_collection.find())

def delete_usuario(user_id: str):
    return usuarios_collection.delete_one({"_id": ObjectId(user_id)})