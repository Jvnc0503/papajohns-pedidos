# **Especificaciones Técnicas y Arquitectura: Sistema de Gestión de Pedidos \- Papa John's**

## **1\. Visión General**

Sistema Serverless EDA (Event Driven Architecture) multi-tenant desarrollado sobre AWS, con integración Multi-nube (Oracle OCI). El sistema gestiona el ciclo de vida de un pedido de comida rápida desde la recepción hasta la entrega o cancelación, utilizando orquestación de tareas humanas y resolución automatizada de fallos.

## **2\. Pila Tecnológica (Stack)**

* **Cloud Core:** AWS (Amplify, API Gateway, EventBridge, Step Functions, Lambda, DynamoDB, S3, SNS, SQS).  
* **Cloud Secundaria:** Oracle OCI (Oracle Functions para integración Rappi).  
* **Patrón de Orquestación:** Wait for Callback with Task Token.  
* **Patrón de Mensajería:** Pub/Sub (Fan-out) y Message Queuing.

## **3\. Especificaciones Funcionales (Lógica de Negocio)**

1. **Multi-tenancy:** Los pedidos están aislados lógicamente por un tenantId.  
2. **Flujos Ramificados:** \* **Flujo Feliz:** Recepción \-\> Cocina \-\> Empaque \-\> Despacho \-\> Entregado.  
   * **Excepciones:** El sistema permite desvíos hacia CANCELADO (decisión humana) o ABANDONO\_OPERATIVO (timeout del sistema).  
3. **Persistencia:** DynamoDB indexada por tenantId (Partition Key) y orderId (Sort Key).

## **4\. Detalles de Implementación Arquitectónica**

### **A. Eventos del Sistema (EventBridge)**

* **Event Type: OrderCreated** \-\> Inicia la ejecución de la Step Function.  
* **Event Type: OrderStatusUpdated** \-\> Gatilla notificaciones externas.

### **B. Orquestación Avanzada (Step Functions)**

* **Integración Nativa:** Utiliza "Resource": "arn:aws:states:::sns:publish.waitForTaskToken" para inyectar el token directo al bus de mensajes.  
* **Nodos Choice:** Evalúan la respuesta del trabajador ($.resultadoTrabajador.nextStage). Si es "CANCELADO", el flujo finaliza anticipadamente.  
* **Nodos Catch:** Atrapan errores "WORKER\_TIMEOUT" inyectados por la DLQ para cerrar transacciones abandonadas.

### **C. Tolerancia a Fallos (Patrón DLQ y Remediation)**

Cada etapa (Cocina, Empaque, Despacho) posee una SQS y una DLQ. Si un trabajador no resuelve el pedido tras 3 intentos (maxReceiveCount: 3), el mensaje envenenado pasa a la DLQ, donde una Lambda rescatista cierra el ciclo operativamente.

## **5\. Componentes del Backend (Funciones Lambda)**

### **1\. createOrder (Productor de Eventos)**

* **Trigger:** API Gateway (POST /tenants/{tenantId}/orders).  
* **Responsabilidad:** Valida payload, inicializa el pedido en DynamoDB y emite el evento asíncrono a EventBridge. No acopla la respuesta al inicio del orquestador.

### **2\. getOrder (Read Model)**

* **Trigger:** API Gateway (GET /tenants/{tenantId}/orders/{orderId}).  
* **Responsabilidad:** Actúa como Single Source of Truth para consultas de los clientes web. Lee desde DynamoDB. No gestiona ni expone Task Tokens.

### **3\. updateOrderStatus (Resolución de Orquestación)**

* **Trigger:** API Gateway (PATCH /tenants/{tenantId}/orders/{orderId}/status).  
* **Responsabilidad:** Invocada por el dashboard web. Actualiza DynamoDB (marcas de tiempo), asegura la idempotencia y utiliza el taskToken para ejecutar send\_task\_success(), permitiendo a Step Functions evaluar el siguiente paso.

### **4\. notifyService (Consumidor Desacoplado)**

* **Trigger:** EventBridge Rule (OrderStatusUpdated).  
* **Responsabilidad:** Si el origen es "RAPPI", ejecuta un webhook POST hacia OCI. Si el estado es "ENTREGADO", genera un JSON estático en S3.

### **5\. processDlq (Remediación Automatizada)**

* **Trigger:** Colas SQS (DlqCocina, DlqEmpaque, DlqDespacho).  
* **Responsabilidad:** Consume mensajes abandonados del mundo físico. Actualiza la BD con estado de error crítico y ejecuta send\_task\_failure() hacia Step Functions para liberar el flujo suspendido.