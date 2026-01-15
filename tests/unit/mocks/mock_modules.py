"""Mock implementations of required modules"""
from unittest.mock import Mock

class Constants:
    POST = "POST"
    GET = "GET"
    PUT = "PUT"
    DELETE = "DELETE"
    STATUS_CODE = "statusCode"
    BODY = "body"
    HEADERS_KEY = "headers"
    HEADERS = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*"
    }

def valida_cors(origin):
    return origin or "*"

class Sucursal:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
