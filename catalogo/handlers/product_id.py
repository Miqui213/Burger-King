import os
import json
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST"
}
PRODUCTS_TABLE = os.environ.get("TABLA_PRODUCTOS", "Burger-Productos-dev")

dynamodb = boto3.resource("dynamodb")
productos_table = dynamodb.Table(PRODUCTS_TABLE)

def _resp(code, payload=None):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(payload or {}, ensure_ascii=False, default=str)
    }

def _parse_body(event):
    body = event.get("body", {})
    if isinstance(body, str):
        return json.loads(body) if body.strip() else {}
    elif not isinstance(body, dict):
        return {}
    return body

def _convert_decimal(obj):
    """Convierte los Decimal de DynamoDB a float/int nativos de Python"""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal(i) for i in obj]
    return obj

def lambda_handler(event, context):
    print("ProductID Event INVOKED")
    
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    if method != "POST":
        return _resp(405, {"error": "Método no permitido. Usa POST."})

    body = _parse_body(event)

    local_id = body.get("local_id")
    producto_id = body.get("producto_id")
    
    if not local_id:
        return _resp(400, {"error": "Falta el campo obligatorio 'local_id' en el body"})
    
    if not producto_id:
        return _resp(400, {"error": "Falta el campo obligatorio 'producto_id' en el body"})
    
    try:
        response = productos_table.get_item(
            Key={
                "local_id": str(local_id).strip(), 
                "producto_id": str(producto_id).strip()
            }
        )
    except ClientError as e:
        print(f"Error DynamoDB: {e}")
        return _resp(500, {"error": "Error interno al buscar el producto"})
    
    if "Item" not in response:
        return _resp(404, {"error": "Producto no encontrado en este local"})
    
    item_limpio = _convert_decimal(response["Item"])
    
    return _resp(200, {"producto": item_limpio})