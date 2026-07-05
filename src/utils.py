import json

STAGES = ["RECEPCION", "COCINA", "EMPAQUE", "DESPACHO", "ENTREGADO", "CANCELADO"]

VALID_TRANSITIONS = {
    "COCINA":    "RECEPCION",
    "EMPAQUE":   "COCINA",
    "DESPACHO":  "EMPAQUE",
    "ENTREGADO": "DESPACHO",
    "CANCELADO": ["RECEPCION", "COCINA"]
}


def response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=str),
    }


def ok(body: dict) -> dict:
    return response(200, body)


def created(body: dict) -> dict:
    return response(201, body)


def bad_request(message: str) -> dict:
    return response(400, {"error": message})


def not_found(message: str) -> dict:
    return response(404, {"error": message})


def server_error(message: str) -> dict:
    return response(500, {"error": message})
