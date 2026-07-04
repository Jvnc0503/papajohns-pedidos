# **Order Service — Papa John's**

Microservicio serverless altamente escalable para la gestión de pedidos de Papa John's. Implementa una **Arquitectura Basada en Eventos** utilizando orquestación de microservicios y patrones de mensajería asíncrona.

## **🚀 Arquitectura y Patrones Implementados**

* **Orquestación Asíncrona:** AWS Step Functions con el patrón *Wait for Callback* (waitForTaskToken).  
* **Patrón Fan-out:** Distribución de tareas mediante temas SNS que alimentan colas SQS específicas por etapa (Cocina, Empaque, Despacho).  
* **Resiliencia y Tolerancia a Fallos:** Uso de *Dead Letter Queues (DLQ)* y una función Lambda "Rescatista" (processDlq) para remediación automatizada de tareas abandonadas.  
* **Flujos Ramificados:** Máquina de estados con nodos Choice (para cancelaciones) y Catch (para timeouts de trabajadores).  
* **Multi-tenancy:** Aislamiento lógico de sucursales a través de tenantId.

## **Estructura**

order-service/  
├── serverless.yml                  \# Infraestructura como Código (IaC)  
├── src/  
│   ├── utils.py                    \# Constantes de estados y helpers HTTP  
│   └── handlers/  
│       ├── create\_order.py         \# POST /orders (Emite OrderCreated)  
│       ├── get\_order.py            \# GET /orders/{id} (Single Source of Truth)  
│       ├── update\_order\_status.py  \# PATCH /orders/{id}/status (Desbloquea Workflow)  
│       ├── notify\_service.py       \# Consumidor EventBridge (S3 y Webhook OCI)  
│       └── process\_dlq.py          \# Consumidor SQS (Remediación de DLQs)

## **Endpoints Principales**

### **POST /orders — Crear pedido**

Inicia la transacción. Guarda en DynamoDB y emite el evento OrderCreated a EventBridge para arrancar Step Functions de forma desacoplada.

### **GET /orders/{id} — Consultar pedido**

Retorna el estado transaccional en vivo del pedido.  
*(Nota: En esta arquitectura EDA, los trabajadores no obtienen sus tareas haciendo polling a este endpoint, sino consumiendo los mensajes directamente de sus colas SQS).*

### **PATCH /orders/{id}/status — Avanzar o Cancelar Etapa**

El trabajador envía su resolución. El backend actualiza la base de datos y envía un SendTaskSuccess a Step Functions usando el taskToken extraído del mensaje SQS. Soporta la transición hacia CANCELADO.

## **Flujo de Estados Válidos**

RECEPCION → COCINA → EMPAQUE → DESPACHO → ENTREGADO  
    ↳ (Opcional) CANCELADO  
