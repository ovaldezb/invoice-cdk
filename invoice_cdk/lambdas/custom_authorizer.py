import json
import jwt
import requests
from jwt.algorithms import RSAAlgorithm

def handler(event, context):
    """
    Custom authorizer para validar tokens de Cognito User Pool
    """
    try:
        token = event['authorizationToken'].replace('Bearer ', '')
        method_arn = event['methodArn']
        
        # Configuración del User Pool
        user_pool_id = "us-east-1_pfcGvfKy1"
        region = "us-east-1"
        
        # Obtener las claves públicas de Cognito
        keys_url = f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}/.well-known/jwks.json'
        jwks = requests.get(keys_url).json()
        
        # Decodificar el header del token para obtener el kid
        headers = jwt.get_unverified_header(token)
        kid = headers['kid']
        
        # Encontrar la clave correcta
        key = None
        for jwk in jwks['keys']:
            if jwk['kid'] == kid:
                key = RSAAlgorithm.from_jwk(json.dumps(jwk))
                break
        
        if not key:
            raise Exception('Public key not found')
        
        # Verificar el token
        payload = jwt.decode(
            token,
            key,
            algorithms=['RS256'],
            audience=None,  # No verificar audience por ahora
            options={"verify_aud": False}
        )
        
        # Verificar que el token es de nuestro User Pool
        if payload.get('iss') != f'https://cognito-idp.{region}.amazonaws.com/{user_pool_id}':
            raise Exception('Invalid issuer')
        
        # Verificar que el token es un access token
        if payload.get('token_use') != 'access':
            raise Exception('Not an access token')
        
        print(f"Token válido para usuario: {payload.get('username')}")
        
        # Generar policy de autorización
        policy = {
            'principalId': payload.get('username'),
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Allow',
                        'Resource': method_arn.split('/')[0] + '/*'
                    }
                ]
            },
            'context': {
                'username': payload.get('username'),
                'sub': payload.get('sub')
            }
        }
        
        return policy
        
    except Exception as e:
        print(f"Error en autorización: {str(e)}")
        raise Exception('Unauthorized')
