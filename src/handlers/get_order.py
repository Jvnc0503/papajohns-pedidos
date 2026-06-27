import os
import boto3

from src.utils import ok, not_found, bad_request, server_error

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["ORDERS_TABLE"]


def handler(event, context):
    order_id = (event.get("pathParameters") or {}).get("id")

    if not order_id:
        return bad_request("Falta el parámetro 'id' en la ruta")

    table = dynamodb.Table(TABLE_NAME)
    result = table.get_item(Key={"orderId": order_id})
    order = result.get("Item")

    if not order:
        return not_found(f"No se encontró el pedido con id '{order_id}'")

    return ok(order)
