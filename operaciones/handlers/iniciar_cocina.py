import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
TABLA_PEDIDOS = os.environ.get('TABLA_PEDIDOS')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        pedido_id = body.get('pedido_id')

        if not pedido_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Falta pedido_id"})}

        table = dynamodb.Table(TABLA_PEDIDOS)
        
        # Actualizamos el estado directamente a "en_preparacion"
        table.update_item(
            Key={'pedido_id': pedido_id},
            UpdateExpression="set estado = :e",
            ExpressionAttributeValues={':e': 'en_preparacion'}
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Producción iniciada exitosamente."})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Error interno del servidor"})}