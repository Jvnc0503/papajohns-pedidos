graph TD
    %% 1. ZONA SUPERIOR: Frontend (Amplify extendido)
    subgraph Frontend [AWS Amplify - Interfaces]
        direction LR
        Web_Client[Web Cliente Papa John's] ~~~ Web_Worker[Dashboard Trabajadores]
    end

    %% 2. ZONA IZQUIERDA: Nube Secundaria (OCI)
    subgraph OCI [Oracle OCI - Mock Rappi]
        direction TB
        OCI_Ingest[Oracle Functions: Enviar Pedido]
        OCI_Webhook[Oracle Functions: Recibir Webhook]
    end

    %% 3. ZONA CENTRAL/INFERIOR: Core Backend AWS
    subgraph Backend [AWS Serverless Backend]
        API_GW[API Gateway]
        DynamoDB[(DynamoDB Multi-tenant)]
        EB_Bus{EventBridge Bus}
        S3_Bucket[(S3 Bucket: Comprobantes)]

        L_CreateOrder(Lambda: createOrder)
        L_UpdateOrder(Lambda: updateOrderStatus)
        L_GetOrder(Lambda: getOrder)
        L_Notify(Lambda: notifyService)
        
        %% NUEVO COMPONENTE: Lambda de Remediación Automatizada
        L_ProcessDLQ(Lambda: processDlq)

        SFN_Orchestrator[[Step Functions: Order Workflow]]
        
        %% Columnas invisibles para mantener SQS y DLQ alineados verticalmente
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

    %% --- ENLACES DE DISTRIBUCIÓN (Gravedad) ---
    Web_Client ~~~ OCI_Ingest

    %% --- DECLARACIÓN DE FLUJOS ---

    %% Flujos de las Colas (Prioridad para el renderizado vertical)
    SNS_Cocina --> SQS_Cocina
    SQS_Cocina -.->|Max retries 3| DLQ_Cocina
    
    SNS_Empaque --> SQS_Empaque
    SQS_Empaque -.->|Max retries 3| DLQ_Empaque
    
    SNS_Despacho --> SQS_Despacho
    SQS_Despacho -.->|Max retries 3| DLQ_Despacho

    %% NUEVO: Consumo de DLQ y Remediación
    DLQ_Cocina --> L_ProcessDLQ
    DLQ_Empaque --> L_ProcessDLQ
    DLQ_Despacho --> L_ProcessDLQ
    
    L_ProcessDLQ -->|Marca ERROR| DynamoDB
    L_ProcessDLQ -->|SendTaskFailure| SFN_Orchestrator

    %% Ingesta (La Web Cliente cae directamente sobre el API Gateway)
    Web_Client -->|POST /orders| API_GW
    OCI_Ingest -->|POST /orders source:RAPPI| API_GW
    
    API_GW --> L_CreateOrder
    API_GW --> L_GetOrder
    L_GetOrder -.->|Consulta Read-Model| DynamoDB
    
    L_CreateOrder -->|Guarda| DynamoDB
    L_CreateOrder -->|Evento: OrderCreated| EB_Bus

    %% Orquestación
    EB_Bus -->|Regla| SFN_Orchestrator
    SFN_Orchestrator -->|waitForTaskToken| SNS_Cocina
    SFN_Orchestrator -->|waitForTaskToken| SNS_Empaque
    SFN_Orchestrator -->|waitForTaskToken| SNS_Despacho

    %% Consumo de Trabajadores (Las flechas suben desde SQS en el Backend hacia el Dashboard)
    SQS_Cocina -.->|Consume SQS| Web_Worker
    SQS_Empaque -.->|Consume SQS| Web_Worker
    SQS_Despacho -.->|Consume SQS| Web_Worker
    
    %% Callback (Desde el Dashboard baja hacia API Gateway)
    Web_Worker -->|PATCH /orders/:id/status| API_GW
    
    API_GW --> L_UpdateOrder
    L_UpdateOrder -->|Actualiza| DynamoDB
    L_UpdateOrder -->|SendTaskSuccess / Cancel| SFN_Orchestrator
    L_UpdateOrder -->|Evento: OrderStatusUpdated| EB_Bus

    %% Notificaciones Multi-nube
    EB_Bus -->|Regla| L_Notify
    L_Notify -.->|POST HTTP| OCI_Webhook
    L_Notify -->|Guarda JSON| S3_Bucket