import json
import os
import boto3
from src.auth_utils import verify_password, generate_jwt
from src.utils import ok, bad_request, response

dynamodb = boto3.resource('dynamodb')
USERS_TABLE = os.environ['USERS_TABLE']
JWT_SECRET = os.environ['JWT_SECRET']

def handler(event, context):
    body = json.loads(event.get('body') or '{}')
    email = body.get('email')
    password = body.get('password')

    if not email or not password:
        return bad_request("Falta credenciales")

    table = dynamodb.Table(USERS_TABLE)
    result = table.get_item(Key={'email': email})
    user = result.get('Item')

    if not user or not verify_password(password, user['passwordHash']):
        return response(401, {"error": "Credenciales inválidas"})

    # Generar Token JWT válido
    token = generate_jwt({"email": email, "name": user['name']}, JWT_SECRET)

    return ok({
        "message": "Login exitoso",
        "token": token,
        "user": {"email": email, "name": user['name']}
    })
