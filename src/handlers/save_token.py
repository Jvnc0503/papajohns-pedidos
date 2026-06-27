import os
import boto3

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ["ORDERS_TABLE"]


def handler(event, context):
    """
    Step Functions invoca este Lambda en cada estado de pausa.
    Guarda el taskToken en el ítem del pedido para que el frontend
    pueda recuperarlo y enviarlo al hacer PATCH /orders/{id}/status.
    """
    order_id   = event["orderId"]
    tenant_id  = event["tenantId"]
    stage      = event["stage"]
    task_token = event["taskToken"]

    table = dynamodb.Table(TABLE_NAME)
    table.update_item(
        Key={"tenantId": tenant_id, "orderId": order_id},  # clave compuesta completa
        UpdateExpression="SET stages.#stage.taskToken = :token",
        ExpressionAttributeNames={"#stage": stage},
        ExpressionAttributeValues={":token": task_token},
    )
    # NO llamar send_task_success aquí — Step Functions queda pausado
    # hasta que update_order_status llame send_task_success con este token.
