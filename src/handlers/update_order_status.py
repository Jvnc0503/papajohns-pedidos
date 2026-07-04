import json
import os
import boto3

from datetime import datetime, timezone
from src.utils import ok, bad_request, not_found, server_error, VALID_TRANSITIONS

dynamodb = boto3.resource("dynamodb")
sfn_client = boto3.client("stepfunctions")

TABLE_NAME = os.environ["ORDERS_TABLE"]

def handler(event, context):
    tenant_id = (event.get("pathParameters") or {}).get("tenantId")
    order_id = (event.get("pathParameters") or {}).get("id")
    if not tenant_id or not order_id:
        return bad_request("Faltan parámetros 'tenantId' o 'id' en la ruta")

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

    # Obtener el pedido actual usando tenantId y orderId
    table = dynamodb.Table(TABLE_NAME)
    result = table.get_item(Key={"tenantId": tenant_id, "orderId": order_id})
    order = result.get("Item")

    if not order:
        return not_found(f"No se encontró el pedido con id '{order_id}' para el tenant '{tenant_id}'")

    current_status = order["status"]

    # --- MEJORA DE RESILIENCIA: Idempotencia ---
    # Si el pedido ya está en el estado destino, retornar éxito sin procesar nada más.
    if current_status == new_status:
        return ok({
            "message": f"El pedido ya se encuentra en el estado '{new_status}'",
            "orderId": order_id,
            "status": new_status,
        })

    # Verificar que la transición es válida
    expected_prev = VALID_TRANSITIONS[new_status]
    
    is_valid_transition = (
        current_status in expected_prev if isinstance(expected_prev, list) 
        else current_status == expected_prev
    )

    if not is_valid_transition:
        return bad_request(
            f"Transición inválida: el pedido está en '{current_status}', "
            f"y no puede pasar a '{new_status}'"
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

    try:
        table.update_item(
            Key={"tenantId": tenant_id, "orderId": order_id},
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
        )
    except Exception as e:
        print(f"Error actualizando DynamoDB: {str(e)}")
        return server_error("Error interno al actualizar la base de datos")

    # Notificar a Step Functions que la etapa fue completada
    if task_token:
        try:
            sfn_client.send_task_success(
                taskToken=task_token,
                output=json.dumps({
                    "orderId":    order_id,
                    "prevStage":  current_status,
                    "nextStage":  new_status,
                    "completedAt": now,
                }),
            )
        except Exception as e:
            # Si falla SFN pero la DB ya se actualizó, logueamos el error. 
            # En un sistema crítico, aquí podríamos considerar una compensación o reintento manual.
            print(f"Error al notificar a Step Functions (Token: {task_token}): {str(e)}")

    # Emitir evento a EventBridge
    try:
        events_client = boto3.client("events")
        events_client.put_events(
            Entries=[{
                "Source": "com.papajohns.orders",
                "DetailType": "OrderStatusUpdated",
                "Detail": json.dumps({
                    "orderId": order_id,
                    "tenantId": tenant_id,
                    "newStatus": new_status,
                    "responsable": responsable,
                    "source": body.get("source", "DASHBOARD")
                }),
                "EventBusName": "default"
            }]
        )
    except Exception as e:
        print(f"Error al emitir evento a EventBridge: {str(e)}")

    return ok({
        "message":    f"Pedido actualizado a '{new_status}'",
        "orderId":    order_id,
        "prevStatus": current_status,
        "newStatus":  new_status,
        "updatedAt":  now,
    })
