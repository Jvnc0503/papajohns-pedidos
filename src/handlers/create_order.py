import json
import os
import uuid
import boto3

from datetime import datetime, timezone
from src.utils import created, bad_request, server_error

dynamodb = boto3.resource("dynamodb")
sfn_client = boto3.client("stepfunctions")

TABLE_NAME = os.environ["ORDERS_TABLE"]
STATE_MACHINE_ARN = os.environ["STATE_MACHINE_ARN"]


def handler(event, context):
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
        "customerName": body["customerName"],
        "items":        items,
        "totalAmount":  body.get("totalAmount", 0),
        "source":       body.get("source", "WEB"),   # WEB | RAPPI (para multi-tenancy luego)
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

    # Guardar en DynamoDB
    table = dynamodb.Table(TABLE_NAME)
    table.put_item(Item=order)

    # Iniciar el workflow en Step Functions
    sfn_client.start_execution(
        stateMachineArn=STATE_MACHINE_ARN,
        name=f"order-{order_id}",
        input=json.dumps({"orderId": order_id}),
    )

    return created({
        "message": "Pedido creado exitosamente",
        "orderId": order_id,
        "status":  order["status"],
    })
