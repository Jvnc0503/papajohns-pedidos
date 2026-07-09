import json
import os
import boto3
from src.auth_utils import hash_password

dynamodb = boto3.resource('dynamodb')
USERS_TABLE = os.environ['USERS_TABLE']

def handler(event, context):
    body = json.loads(event.get('body') or '{}')
    email = body.get('email')
    password = body.get('password')
    name = body.get('name', 'Usuario')

    if not email or not password:
        return {"statusCode": 400, "body": json.dumps({"error": "Falta email o password"})}

    table = dynamodb.Table(USERS_TABLE)
    
    # Verificar si ya existe
    if 'Item' in table.get_item(Key={'email': email}):
        return {"statusCode": 400, "body": json.dumps({"error": "El usuario ya existe"})}

    # Guardar nuevo usuario
    table.put_item(Item={
        'email': email,
        'name': name,
        'passwordHash': hash_password(password)
    })

    return {"statusCode": 201, "body": json.dumps({"message": "Usuario registrado exitosamente"})}
