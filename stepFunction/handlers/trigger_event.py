import json
import boto3
import os

eventbridge = boto3.client('events')

def handler(event, context):
    try:
        body_str = event.get('body', '{}')
        body = json.loads(body_str) if body_str else {}
        
        source = 'burgerking.pedidos'
        detail_type = 'CrearPedido'
        
        respuesta = eventbridge.put_events(
            Entries=[
                {
                    'Source': source,
                    'DetailType': detail_type,
                    'Detail': json.dumps(body),
                    'EventBusName': 'default'
                }
            ]
        )
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "mensaje": "¡AWS recibió el pedido de Oracle y encendió la Step Function!",
                "eventBridge": respuesta
            })
        }
        
    except Exception as e:
        print(f"Error crítico en Lambda: {e}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)})
        }