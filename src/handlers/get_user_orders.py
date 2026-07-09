import json
import os
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
TABLE_NAME = os.environ['ORDERS_TABLE']

def handler(event, context):
    # Extraer el usuario inyectado por el Custom Authorizer
    authorizer = event.get('requestContext', {}).get('authorizer', {})
    user_email = authorizer.get('principalId')

    if not user_email:
        return {"statusCode": 401, "body": json.dumps({"error": "No autorizado"})}

    try:
        table = dynamodb.Table(TABLE_NAME)
        
        # Buscar en el Global Secondary Index usando el correo del usuario
        response = table.query(
            IndexName='UserOrdersIndex',
            KeyConditionExpression=Key('userId').eq(user_email),
            ScanIndexForward=False # Trae los más recientes primero
        )
        
        return {
            "statusCode": 200,
            "headers": {"Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"orders": response.get('Items', [])}, default=str)
        }
    except Exception as e:
        print(f"Error consultando DB: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Error interno"})}
