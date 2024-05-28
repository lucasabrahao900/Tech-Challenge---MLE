from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt 

# SECRET KEY + CRYP ALGORITHM:
SECRET_KEY = "0f8c6d7671a1a845d6c7d21f3b9b4f0dbf9d8d3c4b4a6f9189e6e1a2c5d7e0f8"
ALGORITHM = "HS256"

# USUARIOS PADROES - AUTENTICACAO BASICA
USUARIO_PADRAO = "grupo_mle"
SENHA_PADRAO = "grupo_mle"

app = FastAPI()

# AUTENTITCAO SCHEMA
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# FUNCOES PARA CRIAR E DECODIFICAR O TOKEN DE ACESSO
def create_access_token(data: dict) -> str:
    """
    Cria o token de acesso usando o JWT.
    
    Args:
        data (dict): recebe as informações do usuário para codificar pelo JWT.
    
    Returns:
        token (str): retorna as informações em formato de hash.
    """
    return jwt.encode(data.copy(), SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str):
    """
    Decodifica o token em formato de hash para conferir o usuário.
    
    Args:
        token (str): Token obtido pelo algoritmo.
    
    Returns:
        token decodificado (str): retorna as informações dos usuários decodificados.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None

def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    Verifica se o usuário está autenticado e o token é valido.
    
    Args:
        token (str): Token obtido pelo algoritmo.
    
    Returns:
        token decodificado (str): retorna as informações dos usuários decodificados.
    """
    decoded_token = decode_access_token(token)
    if decoded_token is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Credenciais não válidas!",
            headers = {"WWW-Authenticate": "Bearer"},
        )
    else:
        return decoded_token