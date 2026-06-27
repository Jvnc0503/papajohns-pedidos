# Order Service — Papa John's

Microservicio serverless para la gestión de pedidos. Maneja el ciclo de vida completo de un pedido desde su creación hasta la entrega.

## Estructura

```
order-service/
├── serverless.yml              # Configuración del servicio y recursos AWS
├── src/
│   ├── utils.py                # Helpers de respuesta HTTP y constantes
│   └── handlers/
│       ├── create_order.py     # POST /orders
│       ├── get_order.py        # GET /orders/{id}
│       └── update_order_status.py  # PATCH /orders/{id}/status
```

## Requisitos

- Node.js 18+
- Python 3.11
- AWS CLI configurado con credenciales del Learner Lab
- Serverless Framework v3

```bash
npm install -g serverless
```

## Deploy

```bash
# Configurar credenciales del Learner Lab (copiar de AWS Details)
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_SESSION_TOKEN=...

# Desplegar
cd order-service
serverless deploy --stage dev
```

Al finalizar, Serverless imprime las URLs de cada endpoint.

## Endpoints

### POST /orders — Crear pedido

```bash
curl -X POST https://{api-id}.execute-api.us-east-1.amazonaws.com/dev/orders \
  -H "Content-Type: application/json" \
  -d '{
    "customerName": "Carlos",
    "items": [
      {"name": "Pizza Pepperoni", "qty": 1, "price": 35.90},
      {"name": "Coca Cola", "qty": 2, "price": 8.00}
    ],
    "totalAmount": 51.90
  }'
```

Respuesta:
```json
{
  "message": "Pedido creado exitosamente",
  "orderId": "uuid-generado",
  "status": "RECEPCION"
}
```

### GET /orders/{id} — Consultar pedido

```bash
curl https://{api-id}.execute-api.us-east-1.amazonaws.com/dev/orders/{orderId}
```

Respuesta:
```json
{
  "orderId": "uuid",
  "customerName": "Carlos",
  "items": [...],
  "totalAmount": 51.90,
  "source": "WEB",
  "status": "RECEPCION",
  "stages": {
    "RECEPCION": {"startedAt": "2026-06-27T...", "endedAt": null, "responsable": null},
    "COCINA":    {"startedAt": null, "endedAt": null, "responsable": null},
    ...
  },
  "createdAt": "2026-06-27T...",
  "updatedAt": "2026-06-27T..."
}
```

### PATCH /orders/{id}/status — Avanzar etapa

El worker (cocinero, despachador, repartidor) llama a este endpoint desde el dashboard para confirmar que terminó su etapa. El `taskToken` es el que Step Functions guardó en DynamoDB cuando pausó el workflow.

```bash
curl -X PATCH https://{api-id}.execute-api.us-east-1.amazonaws.com/dev/orders/{orderId}/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "COCINA",
    "responsable": "Juan Cocinero",
    "taskToken": "token-de-step-functions"
  }'
```

## Flujo de estados

```
RECEPCION → COCINA → EMPAQUE → DESPACHO → ENTREGADO
```

Solo se permiten transiciones en ese orden. Intentar saltar o retroceder devuelve 400.

## Tabla DynamoDB

Nombre: `papa-johns-order-service-orders-dev`
Clave primaria: `orderId` (String)

Cada ítem guarda el pedido completo incluyendo el mapa `stages` con timestamps y responsable de cada etapa.
