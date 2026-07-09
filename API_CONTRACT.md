# **🍕 API Contract - Papa John's Order Service (Client API)**

Este documento define la interfaz síncrona HTTP expuesta a través de API Gateway para el ecosistema de clientes (E-commerce). 

> **Nota Arquitectónica:** Las interacciones asíncronas de los trabajadores (como la recepción de tareas vía SQS y la actualización de estados) han sido extraídas de este microservicio y ahora son gestionadas exclusivamente por el **BFF de Empleados**.

## **Configuración Base**

* **Base URL:** `https://{api-id}.execute-api.us-east-1.amazonaws.com/dev`
* **Content-Type:** `application/json`
* **Autenticación:** JWT vía AWS Lambda Custom Authorizer (Cognito/Custom) para rutas protegidas.

---

## **1. Crear Pedido (Cliente / Integración Externa)**

Emite un evento asíncrono al bus del sistema (`OrderCreated`) y arranca el orquestador de Step Functions.

* **Método:** `POST`
* **Ruta:** `/tenants/{tenantId}/orders`
* **Seguridad:** Requiere JWT (Bearer Token).

### **Request Body**
```json
{
  "customerName": "Carlos Mendoza",
  "items": [
    { "name": "Pizza Pepperoni Familiar", "qty": 1, "price": 35.90 }
  ],
  "totalAmount": 35.90,
  "source": "WEB" 
}
```

### **Response: 201 Created**
```json
{
  "message": "Pedido creado exitosamente",
  "orderId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "RECEPCION"
}
```

## **2. Consultar Historial del Usuario (Cliente Web)**

Retorna todos los pedidos asociados al usuario autenticado, separados por estado activo e histórico. Consulta el Global Secondary Index (GSI) de DynamoDB.

* **Método:** `GET`
* **Ruta:** `/tenants/{tenantId}/users/me/orders`
* **Seguridad:** Requiere JWT (Bearer Token). El ID/email se extrae del token, no de la URL.

## **3. Consultar Pedido Específico (Read Model)**

Retorna el Single Source of Truth de un pedido puntual.

* **Método:** `GET`

* **Ruta:** `/tenants/{tenantId}/orders/{orderId}`

* **Seguridad:** Público / Opcional JWT.

### **Response: 200 OK**
```json
{
  "tenantId": "SURCO-01",
  "orderId": "550e8400-e29b-41d4-a716-446655440000",
  "customerName": "Carlos Mendoza",
  "status": "COCINA",
  "stages": {
    "RECEPCION": { "startedAt": "2026-06-27T12:00:00Z", "endedAt": "2026-06-27T12:02:00Z", "responsable": "Sistema" },
    "COCINA": { "startedAt": "2026-06-27T12:02:00Z", "endedAt": null, "responsable": null },
    "EMPAQUE": { "startedAt": null, "endedAt": null, "responsable": null }
  }
}
```
