import json
import boto3
import os
import time

athena = boto3.client('athena')

database = os.environ.get('ATHENA_DATABASE')
salida_s3 = f"s3://{os.environ.get('BUCKET_INGESTA')}/athena-results/"

def lambda_handler(event, context):
    # 1. Definimos las cabeceras CORS para permitir la conexión desde el navegador
    headers_cors = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET"
    }

    auth_context = event.get('requestContext', {}).get('authorizer', {})
    rol = auth_context.get('lambda', {}).get('rol', '').lower()
    
    if rol != 'admin':
        return {
            "statusCode": 403, 
            "headers": headers_cors,  # <-- Inyectamos CORS
            "body": json.dumps({"error": "Acceso restringido al panel analítico."})
        }
        
    try:
        # 2. La consulta SQL con la segmentación por origen que armamos
        query = """
            SELECT 
                estado, 
                origen_pedido, 
                COUNT(*) as cantidad, 
                SUM(CAST(total AS DOUBLE)) as ingresos 
            FROM pedidos_raw 
            GROUP BY estado, origen_pedido;
        """
        
        response_query = athena.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': salida_s3}
        )
        
        execution_id = response_query['QueryExecutionId']
        
        estado_query = 'RUNNING'
        while estado_query in ['RUNNING', 'QUEUED']:
            time.sleep(1)
            estado_res = athena.get_query_execution(QueryExecutionId=execution_id)
            estado_query = estado_res['QueryExecution']['Status']['State']
            
            if estado_query == 'FAILED' or estado_query == 'CANCELLED':
                raise Exception("La consulta en Athena falló.")
                
        resultados = athena.get_query_results(QueryExecutionId=execution_id)
        filas = resultados['ResultSet']['Rows']

        datos_dashboard = []
        for fila in filas[1:]:
            datos = fila['Data']
            datos_dashboard.append({
                "estado": datos[0].get('VarCharValue', 'N/A'),
                "origen": datos[1].get('VarCharValue', 'DESCONOCIDO'),
                "cantidad": int(datos[2].get('VarCharValue', 0)),
                "ingresos": float(datos[3].get('VarCharValue', 0.0))
            })
            
        return {
            "statusCode": 200,
            "headers": headers_cors, # <-- Inyectamos CORS en el éxito
            "body": json.dumps({"metricas": datos_dashboard})
        }
        
    except Exception as e:
        return {
            "statusCode": 500, 
            "headers": headers_cors, # <-- Inyectamos CORS en el error
            "body": json.dumps({"error": f"Fallo en Athena: {str(e)}"})
        }