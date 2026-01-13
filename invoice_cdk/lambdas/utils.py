import os
cors = (os.getenv("CORS") or "*").split(",")

def valida_cors(origin):
    if origin in cors:
        return origin
    return None