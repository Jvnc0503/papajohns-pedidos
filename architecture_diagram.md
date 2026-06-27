graph TD
    %% 1. ZONA SUPERIOR: Frontend
    subgraph Frontend [AWS Amplify - Interfaces]
        Web_Client[Web Cliente Papa John's]
        Web_Worker[Dashboard Trabajadores]
    end

    %% 2. ZONA IZQUIERDA: OCI
    subgraph OCI [Oracle OCI - Mock Rappi]
        OCI_Ingest[Oracle Functions: Enviar Pedido]
        OCI_Webhook[Oracle Functions: Recibir Webhook]
    end

    %% 3. ZONA CENTRAL: Backend
    subgraph Backend [AWS Serverless Backend]
        API_GW[API Gateway]
        DynamoDB[(DynamoDB Multi-tenant)]
        EB_Bus{EventBridge Bus}
        S3_Bucket[(S3 Bucket: Comprobantes)]

        L_CreateOrder(Lambda: createOrder)
        L_UpdateOrder(Lambda: updateOrderStatus)
        L_GetOrder(Lambda: getOrder)
        L_Notify(Lambda: notifyService)

        SFN_Orchestrator[[Step Functions: Order Workflow]]
        
        %% TRUCO DE LIMPIEZA: Columnas invisibles para forzar la verticalidad
        subgraph Col_Cocina [ ]
            style Col_Cocina fill:transparent,stroke:transparent
            SNS_Cocina([SNS: Cocina])
            SQS_Cocina>SQS: Cola Cocina]
            DLQ_Cocina>DLQ: Cocina]
        end

        subgraph Col_Empaque [ ]
            style Col_Empaque fill:transparent,stroke:transparent
            SNS_Empaque([SNS: Empaque])
            SQS_Empaque>SQS: Cola Empaque]
            DLQ_Empaque>DLQ: Empaque]
        end

        subgraph Col_Despacho [ ]
            style Col_Despacho fill:transparent,stroke:transparent
            SNS_Despacho([SNS: Despacho])
            SQS_Despacho>SQS: Cola Despacho]
            DLQ_Despacho>DLQ: Despacho]
        end
    end

    %% --- DECLARACIÓN DE FLUJOS (Orden estricto para evitar cruces) ---

    %% Flujos internos de las columnas rígidas
    SNS_Cocina --> SQS_Cocina
    SQS_Cocina -.->|Max retries| DLQ_Cocina
    
    SNS_Empaque --> SQS_Empaque
    SQS_Empaque -.->|Max retries| DLQ_Empaque
    
    SNS_Despacho --> SQS_Despacho
    SQS_Despacho -.->|Max retries| DLQ_Despacho

    %% Ingesta
    Web_Client -->|POST /orders| API_GW
    OCI_Ingest -->|POST /orders source:RAPPI| API_GW
    API_GW --> L_CreateOrder
    API_GW --> L_GetOrder
    L_GetOrder -.->|Consulta| DynamoDB
    
    L_CreateOrder -->|Guarda| DynamoDB
    L_CreateOrder -->|Evento: OrderCreated| EB_Bus

    %% Orquestación
    EB_Bus -->|Regla| SFN_Orchestrator
    SFN_Orchestrator -->|waitForTaskToken| SNS_Cocina
    SFN_Orchestrator -->|waitForTaskToken| SNS_Empaque
    SFN_Orchestrator -->|waitForTaskToken| SNS_Despacho

    %% Consumo (De SQS al Worker)
    SQS_Cocina -.->|Consume| Web_Worker
    SQS_Empaque -.->|Consume| Web_Worker
    SQS_Despacho -.->|Consume| Web_Worker
    
    %% Callback
    Web_Worker -->|PATCH /orders/:id/status| API_GW
    API_GW --> L_UpdateOrder
    L_UpdateOrder -->|Actualiza| DynamoDB
    L_UpdateOrder -->|SendTaskSuccess| SFN_Orchestrator
    L_UpdateOrder -->|Evento: OrderStatusUpdated| EB_Bus

    %% Notificaciones
    EB_Bus -->|Regla| L_Notify
    L_Notify -.->|POST HTTP| OCI_Webhook
    L_Notify -->|Guarda comprobante JSON| S3_Bucket