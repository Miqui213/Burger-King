import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')
TABLA_PEDIDOS = os.environ.get('TABLA_PEDIDOS')

def lambda_handler(event, context):
    try:
        body = json.loads(event.get('body', '{}'))
        pedido_id = body.get('pedido_id')

        if not pedido_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Falta pedido_id"})}

        table = dynamodb.Table(TABLA_PEDIDOS)
        
        # Rescatamos el ÚLTIMO token (el que dejó entregado.py)
        response = table.get_item(Key={'pedido_id': pedido_id})
        item = response.get('Item', {})
        task_token = item.get('taskToken')

        if not task_token:
            return {"statusCode": 400, "body": json.dumps({"error": "No hay token activo para este pedido"})}

        # Armamos el Payload final
        sfn_output = {
            "status": "CLIENTE_CONFIRMA",
            "input": {
                "pedido_id": pedido_id,
                "mensaje": "El cliente tiene la hamburguesa en sus manos"
            }
        }

        # Despertamos a la Step Function por última vez
        sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps(sfn_output)
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "¡Gracias por confirmar! Buen provecho."})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Error interno del servidor"})}