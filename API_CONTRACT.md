# **🍕 API Contract \- Papa John's Order Service**

Este documento define la interfaz síncrona HTTP expuesta a través de API Gateway. Las interacciones asíncronas (como la entrega de tareas a los trabajadores) se realizan consumiendo directamente desde Amazon SQS, fuera de este contrato REST.

## **Configuración Base**

* **Base URL:** https://{api-id}.execute-api.us-east-1.amazonaws.com/dev  
* **Content-Type:** application/json

## **1\. Crear Pedido (Cliente / Rappi)**

Emite un evento asíncrono al bus del sistema.

* **Método:** POST  
* **Ruta:** /tenants/{tenantId}/orders

### **Request Body**

{  
  "customerName": "Carlos Mendoza",  
  "items": \[  
    { "name": "Pizza Pepperoni Familiar", "qty": 1, "price": 35.90 }  
  \],  
  "totalAmount": 35.90,  
  "source": "WEB"   
}

### **Response: 201 Created**

{  
  "message": "Pedido creado exitosamente",  
  "orderId": "550e8400-e29b-41d4-a716-446655440000",  
  "status": "RECEPCION"  
}

## **2\. Consultar Pedido (Cliente Web)**

Retorna el Single Source of Truth del pedido.

* **Método:** GET  
* **Ruta:** /tenants/{tenantId}/orders/{orderId}

### **Response: 200 OK**

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

*(Nota de Arquitectura: La interfaz del Dashboard de trabajadores no extrae el taskToken de este endpoint. Los trabajadores reciben sus tareas y tokens consumiendo eventos directamente desde sus colas SQS \*queue\*).*

## **3\. Actualizar o Cancelar Pedido (Dashboard Trabajadores)**

Desbloquea el workflow pausado en Step Functions.

* **Método:** PATCH  
* **Ruta:** /tenants/{tenantId}/orders/{orderId}/status

### **Request Body**

{  
  "status": "EMPAQUE",   
  "responsable": "Juan Perez",  
  "taskToken": "AAAAKgAAAAIA..."   
}

* **status**: Estado destino. Puede ser el siguiente estado lógico (EMPAQUE, DESPACHO, ENTREGADO) o puede ser el estado de excepción **CANCELADO** (por ejemplo, falta de ingredientes). Si se envía CANCELADO, Step Functions bifurcará el flujo hacia la finalización.  
* **taskToken**: Extraído previamente del cuerpo del mensaje SQS.

### **Response: 200 OK**

{  
  "message": "Pedido actualizado a 'EMPAQUE'",  
  "orderId": "550e8400-e29b-41d4-a716-446655440000",  
  "prevStatus": "COCINA",  
  "newStatus": "EMPAQUE"  
}  
