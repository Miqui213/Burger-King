import json
import os
import boto3
from datetime import datetime
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource('dynamodb')
TABLE_HISTORIAL_ESTADOS = os.environ['TABLE_HISTORIAL_ESTADOS']
TABLE_PEDIDOS = os.environ.get('TABLE_PEDIDOS')

# CORRECCIÓN 1: Eliminamos el local_id de la llave, igual que hicimos antes
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
    print(f"PedidoEnCocina Event: {json.dumps(event)}")
    
    task_token = event.get('taskToken')
    input_data = event.get('input', {})
    
    # CORRECCIÓN 2: Buscamos 'pedido_id' primero, por si acaso viene así
    order_id = input_data.get('pedido_id') or input_data.get('order_id')
    
    if not order_id:
        print("Error crítico: No llegó el ID del pedido")
        return {"statusCode": 400, "error": "ID no encontrado"}
        
    empleado_id = input_data.get('empleado_id', 'COCINA')
    
    print(f"Procesando order_id: {order_id}")

    update_pedido_estado(order_id, 'en_preparacion')
    
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
        'estado': 'en_preparacion',
        'taskToken': task_token,
        'hora_inicio': timestamp,
        'empleado': empleado_id,
        'details': input_data
    }
    table.put_item(Item=item)
    
    return {
        "status": "EN_COCINA",
        "order_id": order_id,
        "empleado_id": empleado_id
    }