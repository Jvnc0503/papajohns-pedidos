import json
import os
import uuid
import boto3

from decimal import Decimal
from datetime import datetime, timezone
from src.utils import created, bad_request, server_error

dynamodb = boto3.resource("dynamodb")
events_client = boto3.client("events")

TABLE_NAME = os.environ["ORDERS_TABLE"]

def float_to_decimal(obj):
    """Convierte recursivamente todos los float a Decimal para DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [float_to_decimal(i) for i in obj]
    return obj


def handler(event, context):
    tenant_id = (event.get("pathParameters") or {}).get("tenantId")
    if not tenant_id:
        return bad_request("Falta el parámetro 'tenantId' en la ruta")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return bad_request("El body no es JSON válido")

    # Validación de campos obligatorios
    required_fields = ["customerName", "items"]
    missing = [f for f in required_fields if f not in body]
    if missing:
        return bad_request(f"Faltan campos obligatorios: {', '.join(missing)}")

    items = body["items"]
    if not isinstance(items, list) or len(items) == 0:
        return bad_request("'items' debe ser una lista con al menos un producto")

    # Construir el pedido
    order_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    order = {
        "orderId":      order_id,
        "tenantId":     tenant_id,
        "customerName": body["customerName"],
        "items":        items,
        "totalAmount":  body.get("totalAmount", 0),
        "source":       body.get("source", "WEB"),
        "status":       "RECEPCION",
        "stages": {
            "RECEPCION": {"startedAt": now, "endedAt": None, "responsable": None},
            "COCINA":    {"startedAt": None, "endedAt": None, "responsable": None},
            "EMPAQUE":   {"startedAt": None, "endedAt": None, "responsable": None},
            "DESPACHO":  {"startedAt": None, "endedAt": None, "responsable": None},
            "ENTREGADO": {"startedAt": None, "endedAt": None, "responsable": None},
        },
        "createdAt":    now,
        "updatedAt":    now,
    }

    # Convertir floats a Decimal antes de guardar en DynamoDB
    order = float_to_decimal(order)

    # Guardar en DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=order)

    # Emitir evento a EventBridge
    events_client.put_events(
        Entries=[{
            "Source": "com.papajohns.orders",
            "DetailType": "OrderCreated",
            "Detail": json.dumps({
                "orderId":      order_id,
                "tenantId":     tenant_id,
                "customerName": body["customerName"],
                "items":        body["items"],
                "source":       body.get("source", "WEB"),
            }),
            "EventBusName": "default"
        }]
    )

    return created({
        "message": "Pedido creado exitosamente",
        "orderId": order_id,
        "status":  "RECEPCION",
    })
