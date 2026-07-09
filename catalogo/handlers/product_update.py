import os
import json
import base64
import boto3
from decimal import Decimal
from botocore.exceptions import ClientError

PRODUCTS_TABLE = os.environ.get("TABLA_PRODUCTOS", "Burger-Productos-dev")
IMAGES_BUCKET = os.environ.get("BUCKET_PRODUCTOS", "burger-king-productos-bucket")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,PUT"
}

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(PRODUCTS_TABLE)
s3 = boto3.client("s3")
region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"

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
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal(i) for i in obj]
    return obj

def _strip_data_uri(b64s: str):
    if "," in b64s and "base64" in b64s[:64].lower():
        header, content = b64s.split(",", 1)
        if ";base64" in header and ":" in header:
            mime = header.split(":", 1)[1].split(";")[0].strip()
            return content, mime
    return b64s, None

def _map_file_type(file_type: str) -> tuple[str, str]:
    ft = (file_type or "").strip().lower()
    if ft in ("png", "image/png"):
        return "image/png", "png"
    if ft in ("jpg", "jpeg", "image/jpg", "image/jpeg"):
        return "image/jpeg", "jpg"
    raise ValueError("file_type debe ser 'png' o 'jpg/jpeg'")

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

    # --- LÓGICA NUEVA: PROCESAR IMAGEN SI VIENE EN EL PAYLOAD ---
    imagen_b64 = data.pop("imagen_b64", None)
    file_type = data.pop("file_type", None)

    if imagen_b64 and file_type:
        try:
            content_type, ext = _map_file_type(file_type)
            b64_clean, _ = _strip_data_uri(imagen_b64)
            image_bytes = base64.b64decode(b64_clean)
            
            # Reutilizamos el ID del producto para el nombre de la imagen
            object_key = f"{key['local_id']}-{key['producto_id']}.{ext}"
            
            # Subimos a S3
            s3.put_object(
                Bucket=IMAGES_BUCKET,
                Key=object_key,
                Body=image_bytes,
                ContentType=content_type,
            )
            
            # Le inyectamos la nueva URL al diccionario de datos a actualizar
            data["imagen_url"] = f"https://{IMAGES_BUCKET}.s3.{region}.amazonaws.com/{object_key}"
            
        except Exception as e:
            return _resp(500, {"error": f"Error al subir imagen a S3: {str(e)}"})

    # Quitamos los campos prohibidos (por si acaso el frontend los envió)
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