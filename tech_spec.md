# **Especificaciones Técnicas y Arquitectura: Sistema de Gestión de Pedidos - Papa John's**

## **1. Visión General**
Sistema Serverless EDA (Event Driven Architecture) multi-tenant desarrollado sobre AWS, con integración Multi-nube (Oracle OCI). El sistema gestiona el ciclo de vida de un pedido de comida rápida. Para optimizar la seguridad y el rendimiento, la arquitectura implementa el patrón **BFF (Backend for Frontend)**, separando este microservicio de Clientes (Order Service) del microservicio de Empleados (Employee API).

## **2. Pila Tecnológica (Stack)**
* **Cloud Core:** AWS (Amplify, API Gateway, EventBridge, Step Functions, Lambda, DynamoDB, S3, SNS, SQS).
* **Cloud Secundaria:** Oracle OCI (Oracle Functions para integración tipo webhook / Mock Rappi).
* **Patrones de Arquitectura:** Event-Driven, Multi-tenant, API Gateway Custom Authorizer (JWT), Backends for Frontends (BFF).
* **Patrón de Orquestación:** Wait for Callback with Task Token.
* **Patrón de Mensajería:** Pub/Sub (Fan-out) y Message Queuing (SQS + DLQ).

## **3. Especificaciones Funcionales (Lógica de Negocio)**
1. **Multi-tenancy:** Los pedidos están aislados lógicamente por un `tenantId`.
2. **Identidad del Cliente:** Integración de JWT nativo, almacenando el `userId/email` en cada pedido e indexándolo con un GSI para búsquedas en orden cronológico (`ScanIndexForward=False`).
3. **Flujos Ramificados:** * **Flujo Feliz:** Recepción -> Cocina -> Empaque -> Despacho -> Entregado.
   * **Excepciones:** Desvíos hacia `CANCELADO` (decisión humana) o `ABANDONO_OPERATIVO` (timeout del sistema).
4. **Persistencia:** DynamoDB indexada por `tenantId` (Partition Key) y `orderId` (Sort Key).

## **4. Detalles de Implementación Arquitectónica**

### **A. Eventos del Sistema (EventBridge)**
* **Event Type: OrderCreated** -> Desacopla la API Gateway y arranca la ejecución de Step Functions.
* **Event Type: OrderStatusUpdated** -> Gatilla notificaciones externas asíncronas (webhooks / S3).

### **B. Orquestación Avanzada (Step Functions)**
* **Integración Nativa:** Utiliza `"Resource": "arn:aws:states:::sns:publish.waitForTaskToken"` para inyectar el token directo al bus de mensajes (SNS).
* **Nodos Choice / Catch:** Evalúan la respuesta que inyecta la *API de Empleados* para bifurcar el flujo, o atrapan errores `WORKER_TIMEOUT` inyectados por la DLQ.

### **C. Tolerancia a Fallos (Patrón DLQ y Remediation)**
Cada etapa física (Cocina, Empaque, Despacho) posee una SQS y una DLQ. Si un trabajador no resuelve el pedido tras 3 intentos (`maxReceiveCount: 3`), el mensaje envenenado pasa a la DLQ, donde una Lambda rescatista cierra el ciclo operativamente.

## **5. Componentes del Backend (Funciones Lambda)**

> **Nota de Refactorización:** La antigua función `updateOrderStatus` ha sido **deprecada** de este microservicio. La inyección de los *Task Tokens* de vuelta a Step Functions (`send_task_success()`) se realiza ahora desde el microservicio BFF de Empleados.

### **1. customAuthorizer / registerUser / loginUser (Capa de Seguridad)**
* **Responsabilidad:** Gestión de identidades mediante JWT, hasheo PBKDF2 y validación de tokens en API Gateway sin dependencias externas.

### **2. createOrder (Productor de Eventos)**
* **Trigger:** API Gateway (`POST /tenants/{tenantId}/orders`).
* **Responsabilidad:** Valida payload, extrae el `userId` inyectado por el Authorizer, inicializa el pedido en DynamoDB y emite el evento asíncrono a EventBridge.

### **3. getUserOrders (Historial Personalizado)**
* **Trigger:** API Gateway (`GET /tenants/{tenantId}/users/me/orders`).
* **Responsabilidad:** Consulta el GSI `UserOrdersIndex` y clasifica lógicamente los pedidos en progreso e históricos para el frontend del cliente.

### **4. getOrder (Read Model Público)**
* **Trigger:** API Gateway (`GET /tenants/{tenantId}/orders/{orderId}`).
* **Responsabilidad:** Actúa como *Single Source of Truth* para el rastreo en vivo de un pedido individual.

### **5. notifyService (Consumidor Desacoplado Multi-nube)**
* **Trigger:** EventBridge Rule (`OrderStatusUpdated`).
* **Responsabilidad:** Si el origen es "RAPPI", ejecuta un webhook POST hacia Oracle OCI. Si el estado es "ENTREGADO", genera un comprobante inmutable en S3.

### **6. processDlq (Remediación Automatizada)**
* **Trigger:** Colas SQS (`DlqCocina`, `DlqEmpaque`, `DlqDespacho`).
* **Responsabilidad:** Consume mensajes abandonados del mundo físico, marca la BD con error crítico y ejecuta `send_task_failure()` hacia Step Functions para limpiar la ejecución pausada.