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
    
    if rol not in ['rappi', 'admin']:
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