import json
import os
import boto3
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']

def handler(event, context):
    print(f"ReintentarDelivery Event: {json.dumps(event)}")
    
    input_data = event.get('input', {})
    
    # CORRECCIÓN 1: Búsqueda robusta del ID
    order_id = input_data.get('pedido_id') or input_data.get('order_id')
    retry_count = input_data.get('retry_count', 0) + 1
    
    if not order_id:
        print("Error crítico: No llegó el ID del pedido")
        return {"statusCode": 400, "error": "ID no encontrado"}
    
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    timestamp = datetime.utcnow().isoformat()
    
    item = {
        'pedido_id': order_id,
        'estado_id': timestamp,
        'createdAt': timestamp,
        'estado': 'reintentando_delivery', # Nombre más claro para el log
        'hora_inicio': timestamp,
        'empleado': 'SYSTEM_RETRY',
        'details': f"Reintento {retry_count} - Re-evaluando delivery"
    }
    table.put_item(Item=item)
    
    # CORRECCIÓN 2: El escudo contra la amnesia de datos
    # Clonamos todo el carrito y la información original
    output_data = dict(input_data)
    
    # Inyectamos solo las variables de control que necesita Step Functions
    output_data['order_id'] = order_id
    output_data['pedido_id'] = order_id
    output_data['retry_count'] = retry_count
    output_data['status'] = "RETRYING_DELIVERY"
    output_data['empleado_id'] = input_data.get('empleado_id', 'SYSTEM')
    
    return output_data