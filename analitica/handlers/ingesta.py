import json
import boto3
import os
import csv
import io
from datetime import datetime

dynamodb = boto3.resource('dynamodb')
s3 = boto3.client('s3')

tabla_historial = dynamodb.Table(os.environ.get('TABLA_HISTORIAL_ESTADOS'))
bucket_ingesta = os.environ.get('BUCKET_INGESTA')

def lambda_handler(event, context):
    # INYECCIÓN DE CORS
    headers_cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    }

    auth_context = event.get('requestContext', {}).get('authorizer', {})
    lambda_data = auth_context.get('lambda', {})
    rol = lambda_data.get('rol', '').lower()
    
    if rol != 'admin':
        return {
            "statusCode": 403, 
            "headers": headers_cors,
            "body": json.dumps({"error": "Acceso denegado. Se requieren privilegios de Administrador para el Data Lake."})
        }
        
    try:
        respuesta = tabla_historial.scan()
        registros = respuesta.get('Items', [])

        csv_buffer = io.StringIO()
        escritor_csv = csv.writer(csv_buffer)
        
        # 1. CABECERAS: Sincronizadas con la tabla de Athena y selected.csv
        escritor_csv.writerow([
            'pedido_id', 'cliente', 'cocinero_id', 'createdAt', 
            'empaquetador_id', 'estado', 'items', 'origen_pedido', 
            'taskToken', 'total'
        ])
        
        for reg in registros:
            # Manejo seguro para convertir listas/diccionarios de items a JSON string
            items_raw = reg.get('items', [])
            items_str = json.dumps(items_raw) if isinstance(items_raw, (list, dict)) else str(items_raw)

            escritor_csv.writerow([
                reg.get('pedido_id', 'N/A'),
                reg.get('cliente', 'Desconocido'),
                reg.get('cocinero_id', 'Desconocido'),
                reg.get('createdAt', datetime.utcnow().isoformat()),
                reg.get('empaquetador_id', 'Desconocido'),
                reg.get('estado', 'DESCONOCIDO'),
                items_str,
                reg.get('origen_pedido', 'LOCAL'),  # Crucial para tu Dashboard
                reg.get('taskToken', ''),
                str(reg.get('total', 0.0))
            ])
            
        nombre_archivo = f"ingesta_pedidos_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        
        # 2. RUTA S3: Ajustada a la carpeta que lee Athena
        s3.put_object(
            Bucket=bucket_ingesta,
            Key=f"datos_pedidos/{nombre_archivo}", 
            Body=csv_buffer.getvalue()
        )
        
        return {
            "statusCode": 200,
            "headers": headers_cors,
            "body": json.dumps({
                "mensaje": "Pipeline de ingesta ejecutado con éxito",
                "registros_procesados": len(registros),
                "archivo_s3": nombre_archivo
            })
        }
        
    except Exception as e:
        return {
            "statusCode": 500, 
            "headers": headers_cors,
            "body": json.dumps({"error": f"Fallo en la ingesta: {str(e)}"})
        }