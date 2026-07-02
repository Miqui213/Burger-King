import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLA_PEDIDOS'))

def lambda_handler(event, context):
    auth_context = event.get('requestContext', {}).get('authorizer', {})
    lambda_data = auth_context.get('lambda', {})
    rol = lambda_data.get('rol', '').lower()
    usuario_id = lambda_data.get('usuario_id', 'Desconocido')
    
    if rol not in ['empaquetador', 'admin']:
        return {"statusCode": 403, "body": json.dumps({"error": "Solo el EMPAQUETADOR puede ejecutar esto."})}
        
    body = json.loads(event.get('body', '{}'))
    pedido_id = body.get('pedido_id')
    
    table.update_item(
        Key={'pedido_id': pedido_id},
        UpdateExpression="set estado = :e, empaquetador_id = :em",
        ExpressionAttributeValues={':e': 'LISTO_PARA_DELIVERY', ':em': usuario_id}
    )
    
    return {"statusCode": 200, "body": json.dumps({"mensaje": f"Pedido {pedido_id} empaquetado."})}