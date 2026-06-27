# **Especificaciones Técnicas y Arquitectura: Sistema de Gestión de Pedidos \- Papa John's**

## **1\. Visión General**

Sistema Serverless EDA (Event Driven Architecture) multi-tenant desarrollado sobre AWS, con integración Multi-nube (Oracle OCI). El sistema gestiona el ciclo de vida de un pedido de comida rápida desde la recepción hasta la entrega, utilizando orquestación de tareas humanas mediante Step Functions.

## **2\. Pila Tecnológica (Stack)**

* **Cloud Core:** AWS (Amplify, API Gateway, EventBridge, Step Functions, Lambda, DynamoDB, S3, SNS, SQS).  
* **Cloud Secundaria:** Oracle OCI (Oracle Functions para integración Rappi).  
* **Patrón de Orquestación:** Wait for Callback with Task Token.  
* **Comunicación:** EventBridge para eventos asíncronos y SNS/SQS (Fan-out) para distribución de tareas.

## **3\. Especificaciones Funcionales (Lógica de Negocio)**

1. **Multi-tenancy:** Los pedidos deben estar aislados por un tenantId (ID de sucursal).  
2. **Flujo de Trabajo:** Recepción \-\> Cocina \-\> Empaque \-\> Despacho \-\> Entregado.  
3. **Persistencia:** DynamoDB indexada por tenantId y orderId.  
4. **Integración Externa:** \* Origen "RAPPI" desde OCI: Dispara Webhook de retorno.  
   * Estado "ENTREGADO": Genera archivo JSON inmutable en S3.

## **4\. Detalles de Implementación (Para Agentes LLM)**

### **A. Eventos del Sistema (EventBridge Schema)**

* **Event Type: OrderCreated**  
  * Payload: {orderId, tenantId, customerName, items, source}  
* **Event Type: OrderStatusUpdated**  
  * Payload: {orderId, tenantId, newStatus, responsable, source}

### **B. Orquestación y Task Tokens**

La máquina de estados de Step Functions debe definir cada etapa (Cocina, Empaque, Despacho) con el recurso:  
"Resource": "arn:aws:states:::sns:publish.waitForTaskToken"

* **Importante:** El taskToken es obligatorio para que el sistema "sepa" cuándo el trabajador ha terminado la tarea manualmente a través del PATCH /orders/{id}/status.

### **C. Patrón Fan-out SNS/SQS**

Cada etapa de trabajo tiene:

1. **SNS Topic:** Dedicado (ej. SNS-Cocina).  
2. **SQS Queue:** Cola de trabajo vinculada al tópico.  
3. **DLQ (Dead Letter Queue):** Cola de errores asociada con maxReceiveCount: 3 en la RedrivePolicy.

### **D. Seguridad y Tolerancia a Fallos**

* **IAM:** Las Lambdas de updateOrderStatus deben tener permisos states:SendTaskSuccess.  
* **Resiliencia:** El uso de DLQ es obligatorio para todos los flujos de trabajo humano.  
* **Idempotencia:** El taskToken garantiza que el estado de un pedido solo pueda avanzar si el token es válido y no ha sido procesado previamente.

## **5\. Endpoints de API (Contract)**

* POST /tenants/{tenantId}/orders: Inicia el flujo EDA.  
* GET /tenants/{tenantId}/orders/{orderId}: Lectura de estado (Single Source of Truth: DynamoDB).  
* PATCH /tenants/{tenantId}/orders/{orderId}/status: Resolución de callback para el flujo orquestado.

## **6\. Componentes del Backend (Funciones Lambda)**

A continuación, se detallan los 4 microservicios/funciones que componen la lógica del backend:

### **1\. createOrder (Iniciador del Flujo)**

* **Trigger:** API Gateway (POST /tenants/{tenantId}/orders).  
* **Responsabilidad:** \* Recibe el payload inicial (del cliente web o de OCI/Rappi) y valida los datos.  
  * Persiste el pedido en DynamoDB en estado inicial "RECEPCION", usando la clave particionada tenantId y de ordenación orderId.  
  * Emite el evento asíncrono OrderCreated a EventBridge. No interactúa de forma síncrona con Step Functions.

### **2\. getOrder (Consulta de Estado)**

* **Trigger:** API Gateway (GET /tenants/{tenantId}/orders/{orderId}).  
* **Responsabilidad:** \* Actúa como la única fuente de verdad (Single Source of Truth).  
  * Retorna el detalle completo del pedido desde DynamoDB, incluyendo las marcas de tiempo (startedAt, endedAt), el responsable actual y, si existe y está pausado, el taskToken actual para la interfaz de los trabajadores.

### **3\. updateOrderStatus (Resolución de Callback)**

* **Trigger:** API Gateway (PATCH /tenants/{tenantId}/orders/{orderId}/status).  
* **Responsabilidad:** \* Es invocada por el dashboard de trabajadores. Recibe el taskToken y el nuevo estado (ej. de RECEPCION a COCINA).  
  * Actualiza los metadatos transaccionales (tiempos de transición, responsable) en DynamoDB.  
  * Realiza el llamado a stepfunctions.send\_task\_success() utilizando el taskToken, lo cual desbloquea y avanza la máquina de estados.  
  * Emite el evento OrderStatusUpdated a EventBridge.

### **4\. notifyService (Integración Externa y Persistencia Estática)**

* **Trigger:** EventBridge Rule (Escucha eventos OrderStatusUpdated).  
* **Responsabilidad:** \* Lógica totalmente desacoplada para tareas finales.  
  * Si detecta que source \== "RAPPI", realiza una petición POST de webhook hacia Oracle OCI (Nube Secundaria) notificando el nuevo estado.  
  * Si el estado transitado es "ENTREGADO", genera un comprobante estructurado en JSON (recibo) y lo almacena de forma inmutable en Amazon S3.