import json
import os
import boto3
from src.auth_utils import verify_password, generate_jwt

dynamodb = boto3.resource('dynamodb')
USERS_TABLE = os.environ['USERS_TABLE']
JWT_SECRET = os.environ['JWT_SECRET']

def handler(event, context):
    body = json.loads(event.get('body') or '{}')
    email = body.get('email')
    password = body.get('password')

    if not email or not password:
        return {"statusCode": 400, "body": json.dumps({"error": "Falta credenciales"})}

    table = dynamodb.Table(USERS_TABLE)
    result = table.get_item(Key={'email': email})
    user = result.get('Item')

    if not user or not verify_password(password, user['passwordHash']):
        return {"statusCode": 401, "body": json.dumps({"error": "Credenciales inválidas"})}

    # Generar Token JWT válido
    token = generate_jwt({"email": email, "name": user['name']}, JWT_SECRET)

    return {
        "statusCode": 200, 
        "body": json.dumps({
            "message": "Login exitoso",
            "token": token,
            "user": {"email": email, "name": user['name']}
        })
    }
