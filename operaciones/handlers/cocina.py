import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
stepfunctions = boto3.client('stepfunctions')
table = dynamodb.Table(os.environ.get('TABLA_PEDIDOS'))

def lambda_handler(event, context):
    auth_context = event.get('requestContext', {}).get('authorizer', {})
    lambda_data = auth_context.get('lambda', {})
    rol = lambda_data.get('rol', '').lower()
    usuario_id = lambda_data.get('usuario_id', 'Desconocido')
    
    if rol not in ['cocinero', 'admin']:
        return {"statusCode": 403, "body": json.dumps({"error": "Solo el COCINERO puede ejecutar esto."})}
        
    body = json.loads(event.get('body', '{}'))
    pedido_id = body.get('pedido_id')
    
    res = table.get_item(Key={'pedido_id': pedido_id})
    pedido = res.get('Item')
    
    if not pedido:
        return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
    task_token = pedido.get('taskToken')
    
    if task_token:
        stepfunctions.send_task_success(
            taskToken=task_token,
            output=json.dumps({"status": "COCINA_COMPLETA", "pedido_id": pedido_id})
        )
        
    table.update_item(
        Key={'pedido_id': pedido_id},
        UpdateExpression="set estado = :e, cocinero_id = :c",
        ExpressionAttributeValues={':e': 'PRODUCTO_PREPARADO', ':c': usuario_id}
    )
    
    return {"statusCode": 200, "body": json.dumps({"mensaje": f"Pedido {pedido_id} cocinado."})}