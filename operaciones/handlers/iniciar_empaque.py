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
        
        response = table.get_item(Key={'pedido_id': pedido_id})
        item = response.get('Item', {})
        task_token = item.get('taskToken')

        if not task_token:
            return {"statusCode": 400, "body": json.dumps({"error": "No hay token activo para este pedido"})}

        # ¡Despertamos a la Step Function para que pase de 'CocinaCompleta' a 'Empaquetado'!
        sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps({"mensaje": "Empaquetador inició el proceso", "pedido_id": pedido_id})
        )

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Empaque iniciado, Step Function avanzando."})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": "Error interno del servidor"})}