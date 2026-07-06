import json
import os
import boto3

dynamodb = boto3.resource('dynamodb')
sfn = boto3.client('stepfunctions')
TABLE_PEDIDOS = os.environ.get('TABLA_PEDIDOS')

def lambda_handler(event, context):
    print(f"Webhook ConfirmarDelivery: {json.dumps(event)}")
    
    try:
        body = json.loads(event.get('body', '{}'))
        pedido_id = body.get('pedido_id')

        if not pedido_id:
            return {"statusCode": 400, "body": json.dumps({"error": "Falta pedido_id en el cuerpo de la petición"})}

        # 1. Buscar el pedido en DynamoDB para rescatar el Task Token
        table = dynamodb.Table(TABLE_PEDIDOS)
        response = table.get_item(Key={'pedido_id': pedido_id})
        item = response.get('Item', {})
        task_token = item.get('taskToken')

        if not task_token:
            print("Error: No se encontró Task Token válido")
            return {
                "statusCode": 400, 
                "body": json.dumps({"error": "El pedido no está en estado de entrega o ya fue procesado."})
            }

        # 2. Armamos la 'Muñeca Rusa' (Payload) que espera tu Lambda entrega_completa.py
        sfn_output = {
            "input": {
                "pedido_id": pedido_id,
                "order_id": pedido_id,
                "empleado_id": "RAPPI_WEBHOOK" # Identificador para saber que llegó desde otra nube
            }
        }
        
        # 3. Disparamos la señal a AWS Step Functions para que reanude la marcha
        sfn.send_task_success(
            taskToken=task_token,
            output=json.dumps(sfn_output)
        )

        print(f"Señal de éxito enviada a Step Functions para el pedido {pedido_id}")

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Delivery confirmado. Step Functions reanudado exitosamente."})
        }

    except Exception as e:
        print(f"Error confirmando delivery: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}