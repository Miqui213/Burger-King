import json
import boto3

dynamodb = boto3.resource('dynamodb')
sfn_client = boto3.client('stepfunctions')

TABLA = 'Burger-Pedidos-dev'

def lambda_handler(event, context):
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Credentials": True
    }
    
    try:
        body = json.loads(event.get('body', '{}'))
        pedido_id = body.get('pedido_id')

        if not pedido_id:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "Falta pedido_id"})}

        # Aquí es donde ocurría el error porque TABLA estaba vacío
        table = dynamodb.Table(TABLA)
        
        # 2. Rescatamos el Token
        response = table.get_item(Key={'pedido_id': pedido_id})
        item = response.get('Item', {})
        task_token = item.get('taskToken')

        if not task_token:
            return {"statusCode": 400, "headers": headers, "body": json.dumps({"error": "No hay token activo para este pedido."})}

        # 3. Armamos la 'Muñeca Rusa' final
        sfn_output = {
            "status": "ENTREGADO", 
            "input": {
                "pedido_id": pedido_id,
                "mensaje": "El cliente confirmó la recepción"
            }
        }

        # 4. Despertamos la Step Function
        sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps(sfn_output)
        )

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "¡Gracias por confirmar! Buen provecho."})
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        # Ahora el error exacto se enviará al navegador
        return {"statusCode": 500, "headers": headers, "body": json.dumps({"error": f"Fallo interno: {str(e)}"})}