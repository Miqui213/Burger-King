import json
import boto3
import os
import uuid
from datetime import datetime
from decimal import Decimal

dynamodb = boto3.resource('dynamodb')
eventbridge = boto3.client('events')
table = dynamodb.Table(os.environ.get('TABLA_PEDIDOS'))

def handler(event, context):
    try:
        print(f"Evento httpApi recibido: {json.dumps(event)}")
        
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        usuario_id = authorizer_context.get('lambda', {}).get('username') or 'Usuario_Autenticado'
        
        body_str = event.get('body', '{}')
        body = json.loads(body_str) if body_str else {}
        
        pedido_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().isoformat()
        
        total_decimal = Decimal(str(body.get('total', 0)))
        
        nuevo_pedido = {
            "pedido_id": pedido_id,
            "cliente": body.get('cliente', usuario_id),
            "items": body.get('items', []),
            "total": total_decimal,
            "estado": "RECIBIDO",
            "createdAt": timestamp
        }
        
        table.put_item(Item=nuevo_pedido)
        
        nuevo_pedido['total'] = float(total_decimal)
        
        eventbridge.put_events(
            Entries=[{
                'Source': 'burgerking.pedidos',
                'DetailType': 'CrearPedido',
                'Detail': json.dumps(nuevo_pedido),
                'EventBusName': os.environ.get('EVENT_BUS_NAME', 'default')
            }]
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "mensaje": "Pedido recibido y enviado a la cola de procesamiento",
                "pedido_id": pedido_id,
                "estado": "RECIBIDO"
            })
        }
        
    except Exception as e:
        print(f"Fallo en procesamiento: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Error interno en la API de entrada: {str(e)}"})
        }