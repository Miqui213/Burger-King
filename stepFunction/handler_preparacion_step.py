import os
import json
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource("dynamodb")
TABLE_NAME = os.environ.get("TABLE_HISTORIAL_ESTADOS") 
table = dynamodb.Table(TABLE_NAME)

def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def handler(event, context):
    logger.info("Evento recibido: %s", json.dumps(event, ensure_ascii=False))

    task_token = event.get('taskToken')
    input_data = event.get('input', event)

    if not isinstance(input_data, dict):
        return {"ok": False, "error": "Input debe ser un objeto JSON"}

    pedido_id = str(input_data.get("pedido_id", input_data.get("order_id", ""))).strip()
    estado = str(input_data.get("estado", "en_preparacion")).strip()

    if not pedido_id or not estado:
        return {"ok": False, "error": "Faltan pedido_id y/o estado"}

    timestamp = _now_iso()
    item = {
        "pedido_id": pedido_id,
        "estado_id": timestamp,
        "createdAt": timestamp,
        "estado": estado,
    }

    if task_token:
        item["taskToken"] = task_token

    try:
        table.put_item(Item=item)
        logger.info("Historial insertado: %s", json.dumps(item, ensure_ascii=False))
        return {"ok": True, "historial": item}
    except ClientError as e:
        logger.exception("Error al escribir en DynamoDB: %s", e)
        return {"ok": False, "error": str(e)}