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
    stage      = event["stage"]
    task_token = event["taskToken"]

    table = dynamodb.Table(TABLE_NAME)
    table.update_item(
        Key={"orderId": order_id},
        UpdateExpression="SET stages.#stage.taskToken = :token",
        ExpressionAttributeNames={"#stage": stage},
        ExpressionAttributeValues={":token": task_token},
    )

    # NO llamar send_task_success aquí — la función simplemente guarda el token
    # y retorna. Step Functions queda en pausa hasta que update_order_status
    # llame a send_task_success con ese token.
