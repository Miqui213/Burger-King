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
        
        # 1. Obtener usuario del autorizador
        authorizer_context = event.get('requestContext', {}).get('authorizer', {})
        usuario_id = authorizer_context.get('lambda', {}).get('username') or 'Usuario_Autenticado'
        
        body_str = event.get('body', '{}')
        body = json.loads(body_str) if body_str else {}
        
        pedido_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().isoformat()
        
        # 2. Convertir los items para que DynamoDB los acepte (float -> Decimal)
        items_dynamo = []
        for item in body.get('items', []):
            item_copy = item.copy()
            if 'precio' in item_copy:
                item_copy['precio'] = Decimal(str(item_copy['precio']))
            items_dynamo.append(item_copy)
            
        total_decimal = Decimal(str(body.get('total', 0)))
        
        nuevo_pedido = {
            "pedido_id": pedido_id,
            "cliente": usuario_id,
            "items": items_dynamo,
            "total": total_decimal,
            "estado": "RECIBIDO",
            "createdAt": timestamp,
            "origen_pedido": body.get('origen_pedido', 'LOCAL')
        }
        
        # 3. Guardar en DynamoDB
        table.put_item(Item=nuevo_pedido)
        
        # 4. Revertir Decimal a float para que json.dumps no explote al enviarlo a EventBridge
        nuevo_pedido['total'] = float(total_decimal)
        for item in nuevo_pedido['items']:
            if 'precio' in item:
                item['precio'] = float(item['precio'])
        
        # 5. Disparar el evento (que inicia tu Step Function)
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