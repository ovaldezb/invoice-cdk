import json
import base64
import urllib.request

def handler(event, context):
    """
    Authorizer lambda simple que valida tokens de Cognito
    """
    try:
        token = event['authorizationToken'].replace('Bearer ', '')
        method_arn = event['methodArn']
        
        # Validación básica del token
        if not token or len(token) < 50:
            raise ValueError("Token inválido o muy corto")

        # Decodificar payload sin verificar firma (solo para desarrollo/pruebas)
        try:
            # Separar el token JWT
            parts = token.split('.')
            if len(parts) != 3:
                raise ValueError('Token format invalid')
            
            # Decodificar el payload (parte central)
            payload_encoded = parts[1]
            # Agregar padding si es necesario
            payload_encoded += '=' * (4 - len(payload_encoded) % 4)
            payload_decoded = base64.urlsafe_b64decode(payload_encoded)
            payload = json.loads(payload_decoded.decode('utf-8'))
            
            # Verificaciones básicas
            if 'sub' not in payload:
                raise ValueError('Invalid token - no sub claim')

            username = payload.get('username', payload.get('sub'))
            print(f"Usuario autenticado: {username}")
            
        except Exception as e:
            print(f"Error decodificando token: {e}")
            raise ValueError('Unauthorized')
        
        # Generar policy de autorización
        policy = {
            'principalId': username,
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Allow',
                        'Resource': method_arn.replace(method_arn.split('/')[-1], '*')
                    }
                ]
            },
            'context': {
                'username': username,
                'sub': payload.get('sub', '')
            }
        }
        
        print("Autorización exitosa:", policy)
        return policy
        
    except Exception as e:
        print(f"Error en autorización: {str(e)}")
        raise ValueError('Unauthorized')
