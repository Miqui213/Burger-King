import json
import boto3
import os

dynamodb = boto3.resource('dynamodb')
# 1. Agregamos el cliente de Step Functions
stepfunctions = boto3.client('stepfunctions')
table = dynamodb.Table(os.environ.get('TABLA_PEDIDOS'))

def lambda_handler(event, context):
    auth_context = event.get('requestContext', {}).get('authorizer', {})
    lambda_data = auth_context.get('lambda', {})
    rol = lambda_data.get('rol', '').lower()
    usuario_id = lambda_data.get('usuario_id', 'Desconocido')
    
    # Nota: Asegúrate de que el rol 'admin' esté aquí para que puedas probarlo con tu usuario actual
    if rol not in ['empaquetador', 'admin', 'cocina']:
        return {"statusCode": 403, "body": json.dumps({"error": "Solo el EMPAQUETADOR puede ejecutar esto."})}
        
    body = json.loads(event.get('body', '{}'))
    pedido_id = body.get('pedido_id')
    
    # 2. Vamos a buscar el pedido para sacar el Token Secreto
    res = table.get_item(Key={'pedido_id': pedido_id})
    pedido = res.get('Item')
    
    if not pedido:
        return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
    task_token = pedido.get('taskToken')
    
    # 3. Si hay Token, despertamos a la máquina de estados
    if task_token:
        try:
            stepfunctions.send_task_success(
                taskToken=task_token,
                # El output depende de qué espere tu Step Function en el siguiente bloque.
                output=json.dumps({"status": "EMPAQUETADO", "pedido_id": pedido_id})
            )
        except Exception as e:
            print(f"Error despertando a Step Functions: {e}")
    
    # 4. Actualizamos DynamoDB (Lo que ya tenías bien hecho)
    table.update_item(
        Key={'pedido_id': pedido_id},
        UpdateExpression="set estado = :e, empaquetador_id = :em",
        ExpressionAttributeValues={':e': 'LISTO_PARA_DELIVERY', ':em': usuario_id}
    )
    
    return {"statusCode": 200, "body": json.dumps({"mensaje": f"Pedido {pedido_id} empaquetado."})}