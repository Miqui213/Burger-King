import json
import os
import boto3
import uuid
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
TABLE_PEDIDOS = os.environ.get('TABLE_PEDIDOS')

def update_pedido_estado(pedido_id, local_id, nuevo_estado):
    """Actualiza el estado en la tabla de Pedidos (Transaccional)"""
    if not TABLE_PEDIDOS:
        print("Warning: TABLE_PEDIDOS no configurado")
        return False
    try:
        table = dynamodb.Table(TABLE_PEDIDOS)
        table.update_item(
            Key={'local_id': local_id, 'pedido_id': pedido_id},
            UpdateExpression='SET estado = :estado',
            ExpressionAttributeValues={':estado': nuevo_estado}
        )
        print(f"Pedido {pedido_id} actualizado a: {nuevo_estado}")
        return True
    except Exception as e:
        print(f"Error actualizando estado: {e}")
        return False

def handler(event, context):
    print(f"ProcesarPedido Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    input_data = event.get('input', {})

    order_id = (
        input_data.get('detail', {}).get('order_id') or 
        input_data.get('order_id') or 
        input_data.get('pedido_id') or 
        str(uuid.uuid4())
    )
    empleado_id = input_data.get('detail', {}).get('empleado_id') or input_data.get('empleado_id', 'SYSTEM')
    local_id = input_data.get('local_id', 'UNKNOWN')
    
    update_pedido_estado(order_id, local_id, 'procesando')
    
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    timestamp = datetime.utcnow().isoformat()
    
    details_with_local = dict(input_data)
    if 'local_id' not in details_with_local:
        details_with_local['local_id'] = local_id
    
    item = {
        'pedido_id': order_id,
        'estado_id': timestamp,
        'createdAt': timestamp,
        'estado': 'procesando',
        'taskToken': task_token,
        'hora_inicio': timestamp,
        'empleado': empleado_id,
        'details': details_with_local
    }
    table.put_item(Item=item)
    
    return {
        "status": "EN_COCINA",
        "order_id": order_id,
        "empleado_id": empleado_id
    }