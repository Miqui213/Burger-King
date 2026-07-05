import json
import os
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
events = boto3.client('events')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
TABLE_PEDIDOS = os.environ.get('TABLE_PEDIDOS')
EVENT_BUS_NAME = os.environ.get('EVENT_BUS_NAME', 'default')

# CORRECCIÓN 1: Eliminamos el local_id (No necesitamos task_token aquí)
def update_pedido_estado(pedido_id, nuevo_estado):
    """Updates the estado field in the Pedidos table"""
    if not TABLE_PEDIDOS:
        return False
    try:
        table = dynamodb.Table(TABLE_PEDIDOS)
        table.update_item(
            Key={'pedido_id': pedido_id},
            UpdateExpression='SET estado = :estado',
            ExpressionAttributeValues={':estado': nuevo_estado}
        )
        print(f"Updated pedido {pedido_id} estado to: {nuevo_estado}")
        return True
    except Exception as e:
        print(f"Error updating pedido estado: {e}")
        return False

def handler(event, context):
    print(f"PedidoFallido Event: {json.dumps(event)}")
    
    input_data = event.get('input', {})
    
    # CORRECCIÓN 2: Búsqueda robusta del ID (Por cómo Step Functions anida los errores en el Catch)
    order_id = (
        input_data.get('pedido_id') or 
        input_data.get('order_id') or 
        input_data.get('input', {}).get('pedido_id') or
        input_data.get('input', {}).get('order_id')
    )
    
    error_info = input_data.get('error', {})
    
    if not order_id:
        print("Error crítico: No llegó el ID del pedido al manejador de fallos")
        return {"statusCode": 400, "error": "ID no encontrado"}
        
    print(f"Procesando fallo para order_id: {order_id}")
    print(f"Error detectado: {error_info}")
    
    # CORRECCIÓN 3: Actualizamos el estado sin el local_id
    update_pedido_estado(order_id, 'fallido')
    
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    response = table.query(
        KeyConditionExpression=Key('pedido_id').eq(order_id),
        ScanIndexForward=False,
        Limit=1
    )
    if response.get('Items'):
        prev_item = response['Items'][0]
        table.update_item(
            Key={'pedido_id': order_id, 'estado_id': prev_item['estado_id']},
            UpdateExpression='SET hora_fin = :hf',
            ExpressionAttributeValues={':hf': datetime.utcnow().isoformat()}
        )

    timestamp = datetime.utcnow().isoformat()
    item = {
        'pedido_id': order_id,
        'estado_id': timestamp,
        'createdAt': timestamp,
        'estado': 'fallido',
        'hora_inicio': timestamp,
        'hora_fin': timestamp,
        'empleado': 'SYSTEM',
        'details': {
            'error': str(error_info),
            'reason': 'Timeout o rechazo múltiple'
        }
    }
    table.put_item(Item=item)
    
    try:
        events.put_events(
            Entries=[{
                'Source': 'burgerking.pedidos',
                'DetailType': 'PedidoFallido',
                'Detail': json.dumps({
                    'order_id': order_id,
                    'timestamp': timestamp,
                    'error': str(error_info),
                    'message': 'Tu pedido no pudo ser procesado. Por favor contacta con el restaurante.'
                }),
                'EventBusName': EVENT_BUS_NAME
            }]
        )
        print(f"📧 Published PedidoFallido event for order {order_id}")
    except Exception as e:
        print(f"Error publishing event: {e}")
    
    return {
        "status": "FAILED",
        "order_id": order_id,
        "message": "Pedido marcado como fallido y usuario notificado"
    }