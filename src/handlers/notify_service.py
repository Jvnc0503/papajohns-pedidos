import json
import os
import boto3
import urllib.request
from datetime import datetime, timezone

s3_client = boto3.client('s3')
BUCKET_NAME = os.environ['RECEIPTS_BUCKET']
OCI_WEBHOOK_URL = os.environ.get('OCI_WEBHOOK_URL', '') # URL de tu Cloud Function en OCI

def handler(event, context):
    """
    Consumidor de EventBridge. Escucha eventos 'OrderStatusUpdated'.
    Payload esperado en event['detail']: { orderId, source, status, ... }
    """
    detail = event.get('detail', {})
    order_id = detail.get('orderId')
    source = detail.get('source')
    status = detail.get('newStatus')
    
    if not order_id or not status:
        print("Evento inválido, faltan datos.")
        return

    # 1. Lógica Multi-nube: Notificar a Rappi (OCI) si el origen lo requiere
    if source == 'RAPPI' and OCI_WEBHOOK_URL:
        payload = json.dumps({
            "orderId": order_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }).encode('utf-8')
        
        req = urllib.request.Request(OCI_WEBHOOK_URL, data=payload, method='POST')
        req.add_header('Content-Type', 'application/json')
        
        try:
            with urllib.request.urlopen(req) as response:
                print(f"Notificación a OCI exitosa: {response.status}")
        except Exception as e:
            print(f"Error al notificar a OCI: {str(e)}")

    # 2. Lógica S3: Generar comprobante cuando se entregue el pedido
    if status == 'ENTREGADO':
        receipt_key = f"receipts/{order_id}.json"
        receipt_body = json.dumps({
            "orderId": order_id,
            "finalStatus": status,
            "completedAt": datetime.now(timezone.utc).isoformat(),
            "message": "Pedido procesado y entregado exitosamente por Papa Johns."
        }, indent=2)
        
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=receipt_key,
                Body=receipt_body,
                ContentType='application/json'
            )
            print(f"Comprobante guardado en S3: {receipt_key}")
        except Exception as e:
            print(f"Error al guardar en S3: {str(e)}")

    return {"statusCode": 200, "message": "Procesamiento de notificación exitoso"}