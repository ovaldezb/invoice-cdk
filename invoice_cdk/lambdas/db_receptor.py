from receptor import Receptor

def guarda_receptor(receptor: Receptor, receptor_collection):
    return receptor_collection.insert_one(receptor.dict()).inserted_id


def obtiene_receptor_by_rfc(rfc: str, receptor_collection) -> Receptor:
    receptor_data = receptor_collection.find_one({"Rfc": rfc})
    return Receptor(**receptor_data) if receptor_data else None