# **🍕 API Contract \- Papa John's Order Service**

Este documento define la interfaz de comunicación entre las aplicaciones Frontend (Web Cliente y Dashboard Trabajadores) y el Backend Serverless (AWS API Gateway \+ Lambda).

## **Configuración Base**

* **Base URL (Desarrollo):** https://{api-id}.execute-api.us-east-1.amazonaws.com/dev  
* **Content-Type:** application/json  
* **Multi-tenancy:** Todas las rutas incluyen un {tenantId} que representa la sucursal de Papa John's (Ejemplo: SURCO-01, MIRAFLORES-02).

## **1\. Crear Pedido (Cliente / Rappi)**

Crea un nuevo pedido, lo guarda en DynamoDB y emite el evento OrderCreated a EventBridge para iniciar el flujo en Step Functions.

* **Método:** POST  
* **Ruta:** /tenants/{tenantId}/orders  
* **Autorización:** Ninguna (Público)

### **Request Body**
```json
{  
  "customerName": "Carlos Mendoza",  
  "items": [  
    {  
      "name": "Pizza Pepperoni Familiar",  
      "qty": 1,  
      "price": 35.90  
    },  
    {  
      "name": "Gaseosa Coca Cola 1.5L",  
      "qty": 2,  
      "price": 8.00  
    }  
  ],  
  "totalAmount": 51.90,  
  "source": "WEB"   
}
```

*(Nota: source debe ser "WEB" para pedidos desde tu app cliente y "RAPPI" para los pedidos simulados desde OCI).*

### **Response: 201 Created**
```json
{  
  "message": "Pedido creado exitosamente y evento emitido",  
  "orderId": "550e8400-e29b-41d4-a716-446655440000",  
  "status": "RECEPCION"  
}
```
### **Errores Posibles**

* 400 Bad Request: Si falta el customerName o la lista de items está vacía.

## **2\. Consultar Pedido (Cliente / Trabajador)**

Obtiene el detalle completo de un pedido, incluyendo los tiempos de cada etapa.

* **Método:** GET  
* **Ruta:** /tenants/{tenantId}/orders/{orderId}  
* **Autorización:** Ninguna (Público)

### **Request Body**

*Ninguno*

### **Response: 200 OK**
```json
{  
  "tenantId": "SURCO-01",  
  "orderId": "550e8400-e29b-41d4-a716-446655440000",  
  "customerName": "Carlos Mendoza",  
  "items": [...],  
  "totalAmount": 51.90,  
  "source": "WEB",  
  "status": "RECEPCION",  
  "stages": {  
    "RECEPCION": {  
      "startedAt": "2026-06-27T12:00:00Z",  
      "endedAt": null,  
      "responsable": null,  
      "taskToken": "AAAAKgAAAAIA..."   
    },  
    "COCINA": {  
      "startedAt": null,  
      "endedAt": null,  
      "responsable": null  
    },  
    "EMPAQUE": { "startedAt": null, "endedAt": null, "responsable": null },  
    "DESPACHO": { "startedAt": null, "endedAt": null, "responsable": null },  
    "ENTREGADO": { "startedAt": null, "endedAt": null, "responsable": null }  
  },  
  "createdAt": "2026-06-27T12:00:00Z",  
  "updatedAt": "2026-06-27T12:00:00Z"  
}
```
*(Nota: El taskToken solo estará presente en la etapa actual si Step Functions ya lo inyectó).*

### **Errores Posibles**

* 404 Not Found: Si el pedido no existe en ese tenant.

## **3\. Actualizar Estado de Pedido (Dashboard Trabajadores)**

Endpoint utilizado por los trabajadores (Cocinero, Empacador, Repartidor) para confirmar que han terminado su tarea. Reanuda la ejecución en Step Functions.

* **Método:** PATCH  
* **Ruta:** /tenants/{tenantId}/orders/{orderId}/status  
* **Autorización:** Requerida en entorno real (Opcional para el MVP académico)

### **Request Body**
```json
{  
  "status": "COCINA",   
  "responsable": "Juan Perez",  
  "taskToken": "AAAAKgAAAAIA..."   
}
```
* **status**: Representa el estado AL QUE SE VA A PASAR (el nuevo estado). Estados válidos en orden: RECEPCION \-\> COCINA \-\> EMPAQUE \-\> DESPACHO \-\> ENTREGADO.  
* **responsable**: Nombre del trabajador que acaba de tomar la acción.  
* **taskToken**: El token exacto que se recuperó de SQS o de la consulta GET del pedido.

### **Response: 200 OK**
```json
{  
  "message": "Pedido actualizado a 'COCINA'",  
  "orderId": "550e8400-e29b-41d4-a716-446655440000",  
  "prevStatus": "RECEPCION",  
  "newStatus": "COCINA",  
  "updatedAt": "2026-06-27T12:05:00Z"  
}
```
### **Errores Posibles**

* 400 Bad Request: Si se intenta saltar un estado (ej. pasar de RECEPCION a EMPAQUE directamente), o si no se envía el status en el JSON.