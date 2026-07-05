import json
import os
import boto3
import uuid
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
TABLE_PEDIDOS = os.environ.get('TABLA_PEDIDOS') or os.environ.get('TABLE_PEDIDOS')

def update_pedido_estado(pedido_id, nuevo_estado, task_token=None):
    """Actualiza el estado y guarda el token en la tabla de Pedidos"""
    if not TABLE_PEDIDOS:
        print("Warning: TABLE_PEDIDOS no configurado")
        return False
    try:
        table = dynamodb.Table(TABLE_PEDIDOS)
        
        # LA LLAVE CORREGIDA: Solo usamos pedido_id
        llave = {'pedido_id': pedido_id} 
        
        if task_token:
            table.update_item(
                Key=llave,
                UpdateExpression='SET estado = :estado, taskToken = :token',
                ExpressionAttributeValues={':estado': nuevo_estado, ':token': task_token}
            )
        else:
            table.update_item(
                Key=llave,
                UpdateExpression='SET estado = :estado',
                ExpressionAttributeValues={':estado': nuevo_estado}
            )
            
        print(f"Pedido {pedido_id} actualizado con Token: {bool(task_token)}")
        return True
    except Exception as e:
        print(f"Error fatal actualizando estado en DynamoDB: {e}")
        return False
    
def handler(event, context):
    print(f"ProcesarPedido Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    # Aquí es donde viene la información real del pedido
    input_data = event.get('input', {})

    # CORRECCIÓN 1: Buscar en input_data en lugar de event
    pedido_id = input_data.get('pedido_id') or input_data.get('detail', {}).get('pedido_id')
    
    if not pedido_id:
        print("Error: pedido_id no encontrado en input_data")
        return {"statusCode": 400, "body": "Error: pedido_id no encontrado"}
        
    empleado_id = input_data.get('detail', {}).get('empleado_id') or input_data.get('empleado_id', 'SYSTEM')

    # Llamamos a nuestra función de base de datos ya corregida (sin local_id)
    update_pedido_estado(pedido_id, 'procesando', task_token)
    
    table = dynamodb.Table(TABLE_HISTORIAL_ESTADOS)
    timestamp = datetime.utcnow().isoformat()
    
    # Usamos json.loads con parse_float para convertir mágicamente todos los números anidados a Decimal
    details_with_local = json.loads(json.dumps(input_data), parse_float=Decimal)
        
    # CORRECCIÓN 2: El total también debe salir de input_data
    total_raw = input_data.get('total') or input_data.get('detail', {}).get('total', 0)
    total_pedido = Decimal(str(total_raw))
    
    item = {
        'pedido_id': pedido_id,
        'total': total_pedido,
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
        "order_id": pedido_id,
        "empleado_id": empleado_id
    }