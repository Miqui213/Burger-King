import os
import json
import math
import base64
import boto3
from decimal import Decimal
from boto3.dynamodb.conditions import Key, Attr

PRODUCTS_TABLE = os.environ.get("TABLA_PRODUCTOS", "Burger-Productos-dev")

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type,Authorization",
    "Access-Control-Allow-Methods": "OPTIONS,POST"
}

def _resp(code, body):
    return {
        "statusCode": code,
        "headers": {"Content-Type": "application/json", **CORS_HEADERS},
        "body": json.dumps(body, ensure_ascii=False, default=str)
    }

def _parse_body(event):
    body = event.get("body")
    if isinstance(body, str):
        return json.loads(body) if body.strip() else {}
    return body if isinstance(body, dict) else {}

def _safe_int(v, default):
    try:
        return int(v)
    except Exception:
        return default

def _convert_decimal(obj):
    """Convierte los Decimal de DynamoDB a float para que el JSON no falle"""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _convert_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_convert_decimal(i) for i in obj]
    return obj

def _encode_token(lek: dict | None) -> str | None:
    if not lek:
        return None
    return base64.urlsafe_b64encode(json.dumps(lek).encode("utf-8")).decode("ascii")

def _decode_token(tok: str | None) -> dict | None:
    if not tok:
        return None
    try:
        return json.loads(base64.urlsafe_b64decode(tok.encode("ascii")).decode("utf-8"))
    except Exception:
        return None

def lambda_handler(event, context):
    print("ListProduct Event INVOKED")

    method = event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return _resp(204, {})

    if method != "POST":
        return _resp(405, {"error": "Método no permitido. Usa POST."})

    body = _parse_body(event)

    local_id = body.get("local_id")
    if not local_id:
        return _resp(400, {"error": "Falta el campo obligatorio 'local_id' en el body"})

    categoria = body.get("categoria")
    size = _safe_int(body.get("size", body.get("limit", 10)), 10)
    if size <= 0 or size > 100:
        size = 10

    next_token_in = body.get("next_token")
    lek = _decode_token(next_token_in)

    page = None
    if not lek:
        page = _safe_int(body.get("page", 0), 0)
        if page < 0:
            page = 0

    ddb = boto3.resource("dynamodb")
    table = ddb.Table(PRODUCTS_TABLE)

    key_cond = Key("local_id").eq(local_id)

    include_total = bool(body.get("include_total"))
    total = None
    total_pages = None
    
    if include_total:
        total = 0
        count_args = {
            "KeyConditionExpression": key_cond,
            "Select": "COUNT"
        }
        if categoria:
            count_args["FilterExpression"] = Attr("categoria").eq(categoria)
            
        count_lek = None
        while True:
            if count_lek:
                count_args["ExclusiveStartKey"] = count_lek
            rcount = table.query(**count_args)
            total += rcount.get("Count", 0)
            count_lek = rcount.get("LastEvaluatedKey")
            if not count_lek:
                break
                
        total_pages = math.ceil(total / size) if size > 0 else 0
        
        if page is not None and total_pages and page >= total_pages:
            return _resp(200, {
                "contents": [],
                "page": page,
                "size": size,
                "totalElements": total,
                "totalPages": total_pages,
                "next_token": None
            })

    qargs = {
        "KeyConditionExpression": key_cond,
        "Limit": size
    }
    if categoria:
        qargs["FilterExpression"] = Attr("categoria").eq(categoria)

    if lek:
        qargs["ExclusiveStartKey"] = lek
        rpage = table.query(**qargs)
    else:
        skip_lek = None
        if page:
            for _ in range(page):
                if skip_lek:
                    qargs["ExclusiveStartKey"] = skip_lek
                rskip = table.query(**qargs)
                skip_lek = rskip.get("LastEvaluatedKey")
                if not skip_lek:
                    resp = {"contents": [], "page": page, "size": size, "next_token": None}
                    if include_total:
                        resp.update({"totalElements": total, "totalPages": total_pages})
                    return _resp(200, resp)
            
            if skip_lek:
                qargs["ExclusiveStartKey"] = skip_lek
        rpage = table.query(**qargs)

    items = rpage.get("Items", [])
    lek_out = rpage.get("LastEvaluatedKey")
    next_token_out = _encode_token(lek_out)

    items = _convert_decimal(items)

    resp = {"contents": items, "size": size, "next_token": next_token_out}
    if page is not None:
        resp["page"] = page
    if include_total:
        resp.update({"totalElements": total, "totalPages": total_pages})

    return _resp(200, resp)