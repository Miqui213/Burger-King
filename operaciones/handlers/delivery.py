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
    
    # Nota: Dejamos 'admin' para que no tengas problemas al probar desde tu Mesa de Control
    if rol not in ['rappi', 'admin', 'delivery']:
        return {"statusCode": 403, "body": json.dumps({"error": "Solo personal de RAPPI puede despachar."})}
        
    body = json.loads(event.get('body', '{}'))
    pedido_id = body.get('pedido_id')
    
    res = table.get_item(Key={'pedido_id': pedido_id})
    pedido = res.get('Item')
    
    if not pedido:
        return {"statusCode": 404, "body": json.dumps({"error": "Pedido no encontrado"})}
        
    origen_pedido = pedido.get('origen', 'Desconocido')
    
    if "Oracle" in origen_pedido or "Rappi_Service" in origen_pedido:
        estado_final = "ENTREGADO_A_RAPPI_EXTERNO"
    else:
        estado_final = "EN_CAMINO_DELIVERY_LOCAL"
        
    # 2. Rescatamos el Token
    task_token = pedido.get('taskToken')
    
    # 3. Despertamos a la máquina de estados
    if task_token:
        try:
            stepfunctions.send_task_success(
                taskToken=task_token,
                # Le pasamos a la máquina cómo se fue el pedido
                output=json.dumps({
                    "status": "DELIVERY_INICIADO", 
                    "pedido_id": pedido_id,
                    "canal_logistico": estado_final
                })
            )
        except Exception as e:
            print(f"Error despertando a Step Functions: {e}")
            
    # 4. Actualizamos la base de datos
    table.update_item(
        Key={'pedido_id': pedido_id},
        UpdateExpression="set estado = :e, transportista = :t, logistica_canal = :lc",
        ExpressionAttributeValues={':e': estado_final, ':t': usuario_id, ':lc': origen_pedido}
    )
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "pedido_id": pedido_id,
            "origen_detectado": origen_pedido,
            "estado_nuevo": estado_final
        })
    }