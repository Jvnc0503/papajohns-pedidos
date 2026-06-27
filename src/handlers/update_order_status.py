import json
import os
import boto3

from datetime import datetime, timezone
from src.utils import ok, bad_request, not_found, server_error, VALID_TRANSITIONS

dynamodb = boto3.resource("dynamodb")
sfn_client = boto3.client("stepfunctions")

TABLE_NAME = os.environ["ORDERS_TABLE"]


def handler(event, context):
    order_id = (event.get("pathParameters") or {}).get("id")
    if not order_id:
        return bad_request("Falta el parámetro 'id' en la ruta")

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return bad_request("El body no es JSON válido")

    new_status   = body.get("status")
    responsable  = body.get("responsable")   # quién completó la etapa actual
    task_token   = body.get("taskToken")     # token que devuelve Step Functions

    # Validaciones básicas
    if not new_status:
        return bad_request("Falta el campo 'status'")

    if new_status not in VALID_TRANSITIONS:
        return bad_request(
            f"Estado inválido '{new_status}'. "
            f"Estados posibles: {list(VALID_TRANSITIONS.keys())}"
        )

    # Obtener el pedido actual
    table = dynamodb.Table(TABLE_NAME)
    result = table.get_item(Key={"orderId": order_id})
    order = result.get("Item")

    if not order:
        return not_found(f"No se encontró el pedido con id '{order_id}'")

    current_status = order["status"]

    # Verificar que la transición es válida
    expected_prev = VALID_TRANSITIONS[new_status]
    if current_status != expected_prev:
        return bad_request(
            f"Transición inválida: el pedido está en '{current_status}', "
            f"pero para pasar a '{new_status}' debe estar en '{expected_prev}'"
        )

    now = datetime.now(timezone.utc).isoformat()

    # Actualizar stages: cerrar la etapa actual, abrir la nueva
    update_expr = (
        "SET #st = :new_status, updatedAt = :now, "
        "stages.#prev.endedAt = :now, stages.#prev.responsable = :resp, "
        "stages.#next.startedAt = :now"
    )
    expr_names = {
        "#st":   "status",
        "#prev": current_status,
        "#next": new_status,
    }
    expr_values = {
        ":new_status": new_status,
        ":now":        now,
        ":resp":       responsable or "Sin asignar",
    }

    table.update_item(
        Key={"orderId": order_id},
        UpdateExpression=update_expr,
        ExpressionAttributeNames=expr_names,
        ExpressionAttributeValues=expr_values,
    )

    # Notificar a Step Functions que la etapa fue completada
    if task_token:
        sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps({
                "orderId":    order_id,
                "prevStage":  current_status,
                "nextStage":  new_status,
                "completedAt": now,
            }),
        )

    return ok({
        "message":    f"Pedido actualizado a '{new_status}'",
        "orderId":    order_id,
        "prevStatus": current_status,
        "newStatus":  new_status,
        "updatedAt":  now,
    })
