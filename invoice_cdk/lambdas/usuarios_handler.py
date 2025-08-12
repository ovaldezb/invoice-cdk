import json
from http import HTTPStatus
from db_user import (
    add_usuario,
    update_usuario,
    list_usuarios,
    delete_usuario,
)
from usuario import Usuario

headers = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*"
}

def handler(event, context):
    http_method = event["httpMethod"]
    path_parameters = event.get("pathParameters")
    body = event.get("body")
    
    try:
        if http_method == "POST":
            usuario_data = json.loads(body)
            usuario = Usuario(**usuario_data)
            user_id = add_usuario(usuario)
            return {
                "statusCode": HTTPStatus.CREATED,
                "body": json.dumps({"message": "User added", "id": str(user_id)}),
                "headers": headers
            }

        elif http_method == "PUT":
            user_id = path_parameters["id"]
            updated_data = json.loads(body)
            update_usuario(user_id, updated_data)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "User updated"}),
                "headers": headers
            }

        elif http_method == "GET":
            usuarios = list_usuarios()
            for user in usuarios:
                user["_id"] = str(user["_id"])  # Convert ObjectId to string
            
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps(usuarios),
                "headers": headers
            }

        elif http_method == "DELETE":
            user_id = path_parameters["id"]
            delete_usuario(user_id)
            return {
                "statusCode": HTTPStatus.OK,
                "body": json.dumps({"message": "User deleted"}),
                "headers": headers
            }

        else:
            return {
                "statusCode": HTTPStatus.METHOD_NOT_ALLOWED,
                "body": json.dumps({"message": "Method Not Allowed"}),
                "headers": headers
            }

    except Exception as e:
        return {
            "statusCode": HTTPStatus.INTERNAL_SERVER_ERROR,
            "body": json.dumps({"message": str(e)}),
            "headers": headers
        }