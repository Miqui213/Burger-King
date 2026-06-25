import os
import json
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

PRODUCTS_TABLE = os.environ.get("TABLA_PRODUCTOS", "Burger-Productos-dev")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,PUT"
}

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(PRODUCTS_TABLE)

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }

def _parse_body(event):
    body = event.get("body") or "{}"
    if isinstance(body, str):
        body = body if body.strip() else "{}"
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return {}
    return body if isinstance(body, dict) else {}

def _to_decimal(obj):
    """Convierte int/float a Decimal para guardarlo en DynamoDB."""
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(x) for x in obj]
    if isinstance(obj, (bool, type(None), Decimal, str)):
        return obj
    if isinstance(obj, (int, float)):
        return Decimal(str(obj))
    return obj

def _convert_decimal(obj):
    """Convierte los Decimal de DynamoDB a float/int para la respuesta JSON."""
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal(i) for i in obj]
    return obj

def lambda_handler(event, context):
    print("UpdateProduct Event INVOKED")

    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    if method != "PUT":
        return _resp(405, {"error": "Método no permitido. Usa PUT."})

    try:
        authorizer_data = event.get("requestContext", {}).get("authorizer", {}).get("lambda", {})
        rol_usuario = authorizer_data.get("rol", "").upper()
    except Exception:
        rol_usuario = "CLIENTE"

    if rol_usuario not in ("ADMIN", "GERENTE", "ADMINISTRADOR"):
        return _resp(403, {"error": "Acceso denegado: Solo el gerente puede actualizar el menú."})

    raw = _parse_body(event)
    data = _to_decimal(raw)

    local_id = data.pop("local_id", None)
    producto_id = data.pop("producto_id", None)

    if not (local_id and producto_id):
        return _resp(400, {"error": "Faltan las claves obligatorias: local_id y producto_id"})
    
    key = {"local_id": str(local_id).strip(), "producto_id": str(producto_id).strip()}

    for forbidden in ("local_id", "producto_id", "createdAt"):
        data.pop(forbidden, None)

    if not data:
        return _resp(400, {"error": "Body vacío o solo contenía llaves primarias; nada que actualizar"})

    expr_names, expr_values, sets = {}, {}, []
    idx = 0
    for k, v in data.items():
        idx += 1
        name_key = f"#f{idx}"
        value_key = f":v{idx}"
        expr_names[name_key] = k
        expr_values[value_key] = v
        sets.append(f"{name_key} = {value_key}")
        
    update_expr = "SET " + ", ".join(sets)

    try:
        res = table.update_item(
            Key=key,
            UpdateExpression=update_expr,
            ExpressionAttributeNames=expr_names,
            ExpressionAttributeValues=expr_values,
            ConditionExpression="attribute_exists(local_id) AND attribute_exists(producto_id)",
            ReturnValues="ALL_NEW"
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return _resp(404, {"error": "Producto no encontrado en el inventario"})
        return _resp(500, {"error": f"Error al actualizar en base de datos: {e}"})
    except Exception as e:
        return _resp(500, {"error": f"Error inesperado: {e}"})

    item_actualizado = _convert_decimal(res.get("Attributes"))
    
    return _resp(200, {
        "message": "Producto actualizado exitosamente", 
        "producto": item_actualizado
    })