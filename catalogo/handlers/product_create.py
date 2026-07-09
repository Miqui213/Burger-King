import os
import json
import base64
import uuid
from decimal import Decimal, InvalidOperation
from datetime import datetime

import boto3
from botocore.exceptions import ClientError

CORS_HEADERS = {"Access-Control-Allow-Origin": "*"}
PRODUCTS_TABLE = "Burger-Productos-dev"
IMAGES_BUCKET = "burger-king-catalogo-imagenes"

dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
region = "us-east-1"

productos_table = dynamodb.Table(PRODUCTS_TABLE)

CATEGORIA_ENUM = [
    "Combos", "Hamburguesas de Res", "Hamburguesas de Pollo",
    "Papas y Snacks", "Bebidas", "Postres", "King Jr", "Promociones"
]

def _resp(code, payload=None):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(payload or {}, ensure_ascii=False)
    }

def _parse_body(event):
    body = event.get("body", {})
    if isinstance(body, str):
        body = json.loads(body) if body.strip() else {}
    elif not isinstance(body, dict):
        body = {}
    return body

def _to_decimal(n):
    if isinstance(n, Decimal):
        return n
    if isinstance(n, (int, float, str)):
        try:
            return Decimal(str(n))
        except (InvalidOperation, ValueError, TypeError):
            pass
    raise InvalidOperation("No es un número válido")

def _to_int(n):
    if isinstance(n, bool):
        raise ValueError("bool no permitido")
    try:
        return int(str(n))
    except Exception as e:
        raise ValueError("No es un entero válido") from e

def _slug(s: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "-" for ch in s).strip("-")

def _strip_data_uri(b64s: str):
    """Devuelve (base64_puro, mime_hint) si viene como data URI."""
    if "," in b64s and "base64" in b64s[:64].lower():
        header, content = b64s.split(",", 1)
        if ";base64" in header and ":" in header:
            mime = header.split(":", 1)[1].split(";")[0].strip()
            return content, mime
    return b64s, None

def _map_file_type(file_type: str) -> tuple[str, str]:
    """Convierte file_type a (content_type, ext)."""
    ft = (file_type or "").strip().lower()
    if ft in ("png", "image/png"):
        return "image/png", "png"
    if ft in ("jpg", "jpeg", "image/jpg", "image/jpeg"):
        return "image/jpeg", "jpg"
    raise ValueError("file_type debe ser 'png' o 'jpg/jpeg'")

def lambda_handler(event, context):
    print(f"CreateProduct Event INVOKED")

    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    try:
        authorizer_data = event.get("requestContext", {}).get("authorizer", {}).get("lambda", {})
        rol_usuario = authorizer_data.get("rol", "").upper()
    except Exception:
        rol_usuario = "CLIENTE"

    if rol_usuario not in ("ADMIN", "GERENTE", "ADMINISTRADOR"):
        return _resp(403, {"message": "Acceso denegado: Solo el gerente puede agregar productos al menú."})

    body = _parse_body(event)
    required = ["local_id", "nombre", "precio", "categoria", "stock", "imagen_b64", "file_type"]
    for f in required:
        if f not in body:
            return _resp(400, {"message": f"Falta el campo obligatorio: {f}"})

    nombre = body["nombre"]
    if not isinstance(nombre, str) or not nombre.strip():
        return _resp(400, {"message": "El campo 'nombre' debe ser string no vacío"})

    local_id = body["local_id"]
    if not isinstance(local_id, str) or not local_id.strip():
        return _resp(400, {"message": "El campo 'local_id' debe ser string no vacío"})

    try:
        precio = _to_decimal(body["precio"])
        if precio < 0:
            return _resp(400, {"message": "El campo 'precio' debe ser >= 0"})
    except InvalidOperation:
        return _resp(400, {"message": "El campo 'precio' debe ser numérico"})

    descripcion = body.get("descripcion")
    if descripcion is not None and not isinstance(descripcion, str):
        return _resp(400, {"message": "El campo 'descripcion' debe ser string"})

    categoria = body["categoria"]
    if categoria not in CATEGORIA_ENUM:
        return _resp(400, {"message": f"Categoría no válida. Debe ser una de: {CATEGORIA_ENUM}"})

    try:
        stock = _to_int(body["stock"])
    except ValueError:
        return _resp(400, {"message": "El campo 'stock' debe ser un entero"})
    if stock < 0:
        return _resp(400, {"message": "El campo 'stock' debe ser un entero >= 0"})

    imagen_b64 = body["imagen_b64"]
    if not isinstance(imagen_b64, str) or not imagen_b64.strip():
        return _resp(400, {"message": "El campo 'imagen_b64' es requerido"})

    try:
        content_type, ext = _map_file_type(body["file_type"])
    except ValueError as e:
        return _resp(400, {"message": str(e)})

    b64_clean, _hint = _strip_data_uri(imagen_b64)
    try:
        image_bytes = base64.b64decode(b64_clean)
    except Exception as e:
        return _resp(400, {"message": f"imagen_b64 inválida: {e}"})

    producto_id = str(uuid.uuid4())
    codigo_producto = f"{local_id.strip()}-{_slug(nombre)}"
    object_key = f"{codigo_producto}.{ext}"

    try:
        s3.put_object(
            Bucket=IMAGES_BUCKET,
            Key=object_key,
            Body=image_bytes,
            ContentType=content_type,
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "AccessDenied":
            return _resp(403, {"message": "El Lambda no tiene permisos para escribir en el Bucket S3"})
        if code == "NoSuchBucket":
            return _resp(400, {"message": f"El bucket {IMAGES_BUCKET} no existe"})
        return _resp(500, {"message": f"Error S3: {e}"})
    except Exception as e:
        return _resp(500, {"message": f"Error al subir imagen: {e}"})

    imagen_url_https = f"https://{IMAGES_BUCKET}.s3.{region}.amazonaws.com/{object_key}"

    item = {
        "local_id": local_id.strip(),
        "producto_id": producto_id,
        "nombre": nombre.strip(),
        "precio": precio,
        "descripcion": descripcion or "",
        "categoria": categoria,
        "stock": stock,
        "imagen_url": imagen_url_https,
        "createdAt": datetime.utcnow().isoformat()
    }

    try:
        productos_table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(#pk) AND attribute_not_exists(#sk)",
            ExpressionAttributeNames={"#pk": "local_id", "#sk": "producto_id"}
        )
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code == "ConditionalCheckFailedException":
            return _resp(409, {"message": "Ya existe un producto con ese producto_id"})
        return _resp(500, {"message": f"Error al crear el producto en DB: {e}"})

    return _resp(201, {
        "message": "Whopper añadido al menú exitosamente",
        "producto": {
            "local_id": item["local_id"],
            "producto_id": item["producto_id"],
            "nombre": item["nombre"],
            "categoria": item["categoria"],
            "precio": str(item["precio"]),
            "stock": item["stock"],
            "imagen_url": item["imagen_url"]
        }
    })