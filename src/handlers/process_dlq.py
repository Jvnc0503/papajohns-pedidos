import json
import os
import boto3
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
sfn_client = boto3.client("stepfunctions")
TABLE_NAME = os.environ["ORDERS_TABLE"]

def handler(event, context):
    # Una Lambda conectada a SQS recibe los mensajes en una lista llamada 'Records'
    for record in event.get("Records", []):
        try:
            # Como usamos RawMessageDelivery en SNS->SQS, el body es directamente nuestro JSON
            body = json.loads(record["body"])
            
            order_id = body.get("orderId")
            tenant_id = body.get("tenantId")
            task_token = body.get("taskToken")
            stage = body.get("stage", "DESCONOCIDO")
            
            now = datetime.now(timezone.utc).isoformat()
            estado_error = f"ERROR_TIMEOUT_{stage}"

            print(f"Procesando mensaje envenenado para la orden: {order_id} en etapa {stage}")

            # 1. Actualizar la base de datos para reflejar que hubo un problema crítico
            table = dynamodb.Table(TABLE_NAME)
            table.update_item(
                Key={"tenantId": tenant_id, "orderId": order_id},
                UpdateExpression="SET #st = :err, updatedAt = :now, stages.#stg.endedAt = :now, stages.#stg.responsable = :resp",
                ExpressionAttributeNames={
                    "#st": "status",
                    "#stg": stage
                },
                ExpressionAttributeValues={
                    ":err": estado_error,
                    ":now": now,
                    ":resp": "SISTEMA_DLQ_ABANDONO"
                }
            )
            
            # 2. Desbloquear Step Functions enviando un Fallo (Failure)
            if task_token:
                sfn_client.send_task_failure(
                    taskToken=task_token,
                    error="WORKER_TIMEOUT",
                    cause=f"El trabajador abandonó la tarea en la etapa {stage}. El mensaje cayó en la DLQ."
                )
                print(f"TaskFailure enviado a Step Functions para la orden {order_id}")

        except Exception as e:
            print(f"Error procesando registro de la DLQ: {str(e)}")
            # En un entorno real, los errores aquí irían a un sistema de alertas (ej. PagerDuty)
            raise e

    return {"statusCode": 200, "message": "Mensajes de la DLQ procesados correctamente"}