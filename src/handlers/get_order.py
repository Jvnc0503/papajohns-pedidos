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
    result = table.get_item(Key={"tenantId": tenant_id, "orderId": order_id})
    order = result.get("Item")

    if not order:
        return not_found(f"No se encontró el pedido con id '{order_id}' para el tenant '{tenant_id}'")

    # Incluir taskToken si está pausado (ej. en una etapa intermedia)
    # Según tech_spec, getOrder debe retornar el taskToken actual para la interfaz de los trabajadores
    if order["status"] != "ENTREGADO" and order["status"] != "RECEPCION":
        order["taskToken"] = order["stages"].get(order["status"], {}).get("token") # Ajustar según cómo se guarde el token

    return ok(order)
