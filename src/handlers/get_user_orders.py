import os
import boto3
from boto3.dynamodb.conditions import Key
from src.utils import ok, server_error, response

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['ORDERS_TABLE']

def handler(event, context):
    # Extraer el usuario inyectado por el Custom Authorizer
    authorizer = event.get('requestContext', {}).get('authorizer', {})
    user_email = authorizer.get('principalId')

    if not user_email:
        return response(401, {"error": "No autorizado"})

    try:
        table = dynamodb.Table(TABLE_NAME)
        
        # Buscar en el Global Secondary Index usando el correo del usuario
        db_response = table.query(
            IndexName='UserOrdersIndex',
            KeyConditionExpression=Key('userId').eq(user_email),
            ScanIndexForward=False # Trae los más recientes primero
        )
        
        return ok({"orders": db_response.get('Items', [])})
        
    except Exception as e:
        print(f"Error consultando DB: {str(e)}")
        return server_error("Error interno al consultar historial")
