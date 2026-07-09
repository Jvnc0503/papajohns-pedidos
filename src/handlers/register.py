import json
import os
import boto3
from src.auth_utils import hash_password
from src.utils import created, bad_request

dynamodb = boto3.resource('dynamodb')
USERS_TABLE = os.environ['USERS_TABLE']

def handler(event, context):
    body = json.loads(event.get('body') or '{}')
    email = body.get('email')
    password = body.get('password')
    name = body.get('name', 'Usuario')

    if not email or not password:
        return bad_request("Falta email o password")

    table = dynamodb.Table(USERS_TABLE)
    
    # Verificar si ya existe
    if 'Item' in table.get_item(Key={'email': email}):
        return bad_request("El usuario ya existe")

    # Guardar nuevo usuario
    table.put_item(Item={
        'email': email,
        'name': name,
        'passwordHash': hash_password(password)
    })

    return created({"message": "Usuario registrado exitosamente"})
