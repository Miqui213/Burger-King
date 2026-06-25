import os
import boto3
import jwt

dynamodb = boto3.resource('dynamodb')
TABLA_TOKENS = os.environ.get('TABLA_TOKENS')
JWT_SECRET = os.environ.get('JWT_SECRET', 'burger-king-secret-2026')

def lambda_handler(event, context):
    print("ValidarToken Event INVOKED")
    
    headers = event.get('headers', {})
    auth_header = headers.get('authorization', '')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        print("Acceso denegado: No se encontró el token Bearer")
        return {"isAuthorized": False}
        
    token = auth_header.split(' ')[1]
    
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        username = payload.get('sub')
        rol = payload.get('rol')
        
        table = dynamodb.Table(TABLA_TOKENS)
        response = table.get_item(Key={'token_id': token})
        
        if 'Item' not in response:
            print(f"Acceso denegado: El token de {username} ya no es válido o la sesión expiró")
            return {"isAuthorized": False}
            
        print(f"Acceso permitido para: {username} (Rol: {rol})")

        return {
            "isAuthorized": True,
            "context": {
                "username": username,
                "rol": rol
            }
        }
        
    except jwt.ExpiredSignatureError:
        print("Acceso denegado: El token ha expirado")
        return {"isAuthorized": False}
    except jwt.InvalidTokenError as e:
        print(f"Acceso denegado: Token malformado o inválido ({str(e)})")
        return {"isAuthorized": False}
    except Exception as e:
        print(f"Error interno en el autorizador: {str(e)}")
        return {"isAuthorized": False}