import os
import json
import boto3
from decimal import Decimal
from urllib.parse import urlparse
from botocore.exceptions import ClientError

PRODUCTS_TABLE = os.environ.get("TABLA_PRODUCTOS", "Burger-Productos-dev")
PRODUCTS_BUCKET = os.environ.get("BUCKET_PRODUCTOS", "")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,DELETE"
}

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
table = dynamodb.Table(PRODUCTS_TABLE)

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False),
    }

def _parse_body(event):
    body = event.get("body") or {}
    if isinstance(body, str):
        body = json.loads(body) if body.strip() else {}
    elif not isinstance(body, dict):
        body = {}
    return body

def _convert_decimal(obj):
    if isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal(i) for i in obj]
    return obj

def _parse_s3_from_url(url: str):
    """Extrae el bucket y el key de una URL de S3 para poder borrar el archivo físico."""
    if not isinstance(url, str) or not url:
        return (None, None)
    u = urlparse(url)
    if u.scheme == "s3":
        return (u.netloc, u.path.lstrip("/"))
    if u.scheme in ("http", "https"):
        host = u.netloc or ""
        path = u.path or ""
        if ".s3." in host and host.count(".") >= 3:
            bucket = host.split(".s3.", 1)[0]
            key = path.lstrip("/")
            return (bucket, key)
        if host.startswith("s3.") and path.count("/") >= 2:
            parts = path.split("/", 2)
            bucket = parts[1]
            key = parts[2] if len(parts) > 2 else ""
            return (bucket, key)
    return (None, None)

def lambda_handler(event, context):
    print("DeleteProduct Event INVOKED")
    
    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    if method != "DELETE":
        return _resp(405, {"error": "Método no permitido. Usa DELETE."})

    try:
        authorizer_data = event.get("requestContext", {}).get("authorizer", {}).get("lambda", {})
        rol_usuario = authorizer_data.get("rol", "").upper()
    except Exception:
        rol_usuario = "CLIENTE"

    if rol_usuario not in ("ADMIN", "GERENTE", "ADMINISTRADOR"):
        return _resp(403, {"error": "Permiso denegado: Solo el gerente puede eliminar productos del menú."})

    data = _parse_body(event)
    local_id = data.get("local_id")
    producto_id = data.get("producto_id")

    if not local_id:
        return _resp(400, {"error": "Falta el campo local_id en el body"})
    if not producto_id:
        return _resp(400, {"error": "Falta el campo producto_id en el body"})

    try:
        res = table.get_item(Key={"local_id": str(local_id).strip(), "producto_id": str(producto_id).strip()})
    except ClientError as e:
        return _resp(500, {"error": f"Error interno al buscar el producto: {e}"})

    if "Item" not in res:
        return _resp(404, {"error": "Producto no encontrado"})

    product = res["Item"]
    image_url = product.get("imagen_url")
    bucket, key = _parse_s3_from_url(image_url) if image_url else (None, None)

    if not bucket and image_url and image_url == image_url.strip() and "/" in image_url and not image_url.startswith(("http://", "https://", "s3://")):
        bucket = PRODUCTS_BUCKET or None
        key = image_url

    if bucket and key:
        try:
            s3.delete_object(Bucket=bucket, Key=key)
            print(f"🗑️ Imagen eliminada de S3: {key}")
        except ClientError as e:
            print(f"⚠️ Advertencia: No se pudo eliminar la imagen de S3: {e}")

    try:
        del_res = table.delete_item(
            Key={"local_id": str(local_id).strip(), "producto_id": str(producto_id).strip()},
            ConditionExpression="attribute_exists(local_id) AND attribute_exists(producto_id)",
            ReturnValues="ALL_OLD"
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return _resp(404, {"error": "El producto ya había sido eliminado o no existe"})
        return _resp(500, {"error": f"Error al eliminar producto de la base de datos: {e}"})

    deleted_attributes = _convert_decimal(del_res.get("Attributes") or {})
    
    return _resp(200, {
        "message": "Producto y recursos asociados eliminados exitosamente", 
        "deleted": deleted_attributes
    })