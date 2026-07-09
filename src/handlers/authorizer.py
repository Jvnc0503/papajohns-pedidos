import os
from src.auth_utils import verify_jwt

JWT_SECRET = os.environ['JWT_SECRET']

def generate_policy(principal_id, effect, resource):
    """Genera la política IAM requerida por API Gateway"""
    return {
        "principalId": principal_id, # El email del usuario
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{
                "Action": "execute-api:Invoke",
                "Effect": effect,
                "Resource": resource
            }]
        }
    }

def handler(event, context):
    # API Gateway manda el token en 'authorizationToken'
    token = event.get('authorizationToken', '')
    
    # Limpiar el token si viene como "Bearer xxxx..."
    if token.startswith('Bearer '):
        token = token.split(' ')[1]

    try:
        # Si el token es válido, extraemos el payload
        payload = verify_jwt(token, JWT_SECRET)
        email = payload.get('email')
        
        # Permitir el acceso y pasar el email como 'principalId'
        return generate_policy(email, 'Allow', event['methodArn'])
    except Exception:
        # Denegar el acceso
        return generate_policy('unauthorized', 'Deny', event['methodArn'])
