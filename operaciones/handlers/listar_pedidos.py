import json
import boto3
import os
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ.get('TABLA_PEDIDOS'))

def lambda_handler(event, context):
    print("ListarPedidos INVOKED")
    try:
        # Hacemos un barrido a la tabla para traer todos los pedidos
        respuesta = table.scan()
        pedidos = respuesta.get('Items', [])
        
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(pedidos, cls=DecimalEncoder)
        }
    except Exception as e:
        print(f"Error al listar: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": "Error interno al obtener los pedidos"})
        }