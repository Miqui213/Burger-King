import json
import boto3
import os
from decimal import Decimal

# Esta clase mágica le enseña a json.dumps cómo convertir Decimals a float
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLA_PEDIDOS'))

def handler(event, context):
    try:
        path_parameters = event.get('pathParameters', {}) or {}
        pedido_id = path_parameters.get('pedido_id')
        
        if not pedido_id:
            return {
                "statusCode": 400,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": "Parámetro 'pedido_id' requerido en la ruta"})
            }

        respuesta = table.get_item(Key={'pedido_id': pedido_id})
        item = respuesta.get('Item')
        
        if not item:
            return {
                "statusCode": 404,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": f"El pedido con ID {pedido_id} no fue localizado"})
            }
            
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            # Aquí inyectamos el Encoder mágico
            "body": json.dumps(item, cls=DecimalEncoder)
        }
        
    except Exception as e:
        print(f"Fallo en consulta: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": f"Error interno al consultar la base de datos: {str(e)}"})
        }