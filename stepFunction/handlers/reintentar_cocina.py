import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']

def handler(event, context):
    print(f"ReintentarCocina Event: {json.dumps(event)}")
    
    input_data = event.get('input', {})
    order_id = input_data.get('order_id')
    retry_count = input_data.get('retry_count', 0) + 1
    
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'pedido_id': order_id,
        'estado_id': timestamp,
        'createdAt': timestamp,
        'estado': 'procesando',
        'hora_inicio': timestamp,
        'empleado': 'SYSTEM_RETRY',
        'details': f"Reintento {retry_count} - Re-evaluando cocina"
    }
    table.put_item(Item=item)
    
    return {
        "order_id": order_id,
        "retry_count": retry_count,
        "status": "RETRYING",
        "empleado_id": input_data.get('empleado_id', 'SYSTEM')
    }