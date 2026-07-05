import os
import boto3

from src.utils import ok, not_found, bad_request, server_error

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["ORDERS_TABLE"]

def handler(event, context):
    tenant_id = (event.get("pathParameters") or {}).get("tenantId")
    order_id = (event.get("pathParameters") or {}).get("id")

    if not tenant_id or not order_id:
        return bad_request("Faltan parámetros 'tenantId' o 'id' en la ruta")

    table = dynamodb.Table(TABLE_NAME)
    
    try:
        result = table.get_item(Key={"tenantId": tenant_id, "orderId": order_id})
        order = result.get("Item")

        if not order:
            return not_found(f"No se encontró el pedido con id '{order_id}' para el tenant '{tenant_id}'")

        # La función ahora cumple un único propósito: 
        # Retornar el estado actual de la base de datos (Single Source of Truth)
        return ok(order)
        
    except Exception as e:
        print(f"Error al consultar la base de datos: {str(e)}")
        return server_error("Error interno al consultar el pedido")