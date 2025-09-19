import json
import jwt  # PyJWT
import os
from jwt import PyJWKClient

USERPOOL_ID = os.getenv("COGNITO_USERPOOL_ID", "us-east-1_pfcGvfKy1")
REGION = os.getenv("AWS_REGION", "us-east-1")
AUDIENCE = os.getenv("COGNITO_AUDIENCE", "tfts8oboht5vbs12dsoie8ecs")

JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}/.well-known/jwks.json"

# Crear cliente JWK una sola vez (PyJWKClient internamente hace caching)
_jwk_client = PyJWKClient(JWKS_URL)

def lambda_handler(event, context):
    print("Evento recibido:", json.dumps(event))
    token = event.get("authorizationToken", "")
    if not token.startswith("Bearer "):
        raise Exception("Unauthorized")

    token = token.split(" ", 1)[1]

    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token).key
        decoded = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=f"https://cognito-idp.{REGION}.amazonaws.com/{USERPOOL_ID}"
        )
        principal_id = decoded.get("sub", "user")
        return generate_policy(principal_id, "Allow", event["methodArn"], decoded)

    except jwt.ExpiredSignatureError:
        print("Token expirado")
        raise Exception("Unauthorized")
    except Exception as e:
        print("Error validando token:", str(e))
        raise Exception("Unauthorized")

def generate_policy(principal_id, effect, resource, context_data=None):
    auth_response = {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {"Action": "execute-api:Invoke", "Effect": effect, "Resource": resource}
            ]
        }
    }
    if context_data:
        auth_response["context"] = {k: str(v) for k, v in context_data.items()}
    return auth_response