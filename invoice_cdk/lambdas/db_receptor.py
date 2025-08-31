from receptor import Receptor

def guarda_receptor(receptor: Receptor, receptor_collection):
    return receptor_collection.insert_one(receptor.dict()).inserted_id


def obtiene_receptor_by_rfc(rfc: str, receptor_collection) -> Receptor:
    return receptor_collection.find_one({"Rfc": rfc})

def update_receptor(id_receptor: str, receptor: Receptor, receptor_collection):
    return receptor_collection.update_one({"_id": id_receptor}, {"$set": receptor.dict()})

