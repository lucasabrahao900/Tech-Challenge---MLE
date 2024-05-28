import os
from datetime import datetime, timedelta
from fastapi import Depends, FastAPI, HTTPException, status
import requests
from bs4 import BeautifulSoup
import json
import re
from unicodedata import normalize
from utils import *



# CRIANDO FUNCOES AUXILIARES PARA A ROTA DA EMBRAPA
def converte_para_inteiro(value: str) -> int:
    """
    Converte uma string para um inteiro, removendo pontos e espaços desnecessários.
    
    Args:
        value (str): A string a ser convertida.
    
    Returns:
        int: O valor inteiro convertido. Retorna 0 em caso de falha na conversão.
    """
    try:
        return int(value.strip().replace(".", ""))
    except:
        return 0

def ajusta_nome_atributo(value: str) -> str:
    """
    Ajusta o nome do atributo para um formato padronizado em maiúsculas e sem acentos.
    
    Args:
        value (str): O nome do atributo a ser ajustado.
    
    Returns:
        str: O nome do atributo ajustado.
    """
    return normalize('NFKD', value).encode('ascii','ignore').decode("ascii").upper().strip()

def cria_url_request(id_aba: str, id_ano: int, id_categoria: str = None) -> str:
    """
    Cria a URL de requisição com base nos parâmetros fornecidos.
    
    Args:
        id_aba (str): Identificador da aba (e.g., "producao", "comercializacao").
        id_ano (int): Ano da consulta.
        id_categoria (str, optional): Categoria da consulta. Default é None.
    
    Returns:
        str: A URL formatada para a requisição.
    """
    dict_opts = {
        "producao": "opt_02",
        "comercializacao": "opt_04",
        "processamento": "opt_03",
        "importacao": "opt_05",
        "exportacao": "opt_06"
    }
    opc = dict_opts[id_aba]

    if id_categoria is not None:
        dict_sub_opts = {
            "viniferas": "subopt_01",
            "vinhos_de_mesa": "subopt_01",
            "americanas_e_hibridas": "subopt_02",
            "espumante": "subopt_02",
            "uvas_de_mesa": "subopt_03",
            "uvas_frescas": "subopt_03"
        }

        if id_categoria in dict_sub_opts:
            sub_opc = f"{opc}&subopcao={dict_sub_opts[id_categoria]}"
        elif id_aba == "importacao" and id_categoria == "suco_de_uva":
            sub_opc = f"{opc}&subopcao=&subopcao=subopt_05"
        else:
            sub_opc = f"{opc}&subopcao=&subopcao=subopt_04"

        return f"http://vitibrasil.cnpuv.embrapa.br/index.php?ano={id_ano}&opcao={sub_opc}"
    else: 
        return f"http://vitibrasil.cnpuv.embrapa.br/index.php?ano={id_ano}&opcao={opc}"

def consultar_url(id_aba: str, id_ano: int, id_categoria: str = None) -> json:
    """
    Consulta a URL gerada e processa os dados da tabela retornada.
    
    Args:
        id_aba (str): Identificador da aba (e.g., "producao", "comercializacao").
        id_ano (int): Ano da consulta.
        id_categoria (str, optional): Categoria da consulta. Default é None.
    
    Returns:
        json: Os dados processados em formato JSON.
    
    Raises:
        HTTPException: Se houver falha na requisição ou na criação do JSON.
    """

    url = cria_url_request(id_aba, id_ano, id_categoria)
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, 'html.parser')
        tb_geral = soup.find_all(class_ = 'tb_base tb_dados')
        data = {}
        if id_aba in ["producao", "comercializacao", "processamento"]:
            for tb_sub in tb_geral:
                lista_linhas = tb_sub.find_all('tr')
                atributo = ""
                for linha in lista_linhas:
                    lista_filtrada = [elemento.strip() for elemento in linha.get_text().split("  ") if elemento.strip()]
                    if "tb_subitem" in str(linha):
                        data[ajusta_nome_atributo(atributo)][ajusta_nome_atributo(lista_filtrada[0])] = converte_para_inteiro(lista_filtrada[1])
                    if "tb_item" in str(linha):
                        atributo = lista_filtrada[0]
                        data[ajusta_nome_atributo(atributo)] = {"TOTAL": converte_para_inteiro(lista_filtrada[1])}
        else:
            for tb_sub in tb_geral:
                linhas = tb_sub.find_all('tr')
                for linha in linhas[1:]:
                    formatado = re.sub(r"  |\n|<tr>|</tr>|</td>", '', str(linha)).split("<td>")
                    data[ajusta_nome_atributo(formatado[1])] = {"QUANTIDADE": converte_para_inteiro(formatado[2]), "VALOR": converte_para_inteiro(formatado[3])}

        try:
            return data #json.dumps(data, ensure_ascii=False, indent=4)
        except:
            print(f"{datetime.now()} - Erro ao criar o JSON do request.")
            raise HTTPException(
                status_code = 500,
                detail = "Erro ao criar o JSON do request"
            )
    else:
        print(f"{datetime.now()} - Erro ao criar o JSON do request.")
        raise HTTPException(
            status_code = 500,
            detail = "Erro ao criar o JSON do request"
        )

# ROTA DE SOLICITACAO DO TOKEN - NECESSARIO A UTILIZACAO DO LOGIN PADRAO
@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    if form_data.username != USUARIO_PADRAO or form_data.password != SENHA_PADRAO:
        raise HTTPException(
            status_code = 400,
            detail = "Usuário ou senha incorretos!"
        )
    else:
        return {
            "access_token": create_access_token(data={"sub": form_data.username}), 
            "token_type": "bearer"
        }


@app.get("/{id_aba}/{id_ano}/")
async def read_root(id_aba: str, id_ano: int, id_categoria: str = None, current_user: dict = Depends(get_current_user)):
    """
    Rota principal do FastAPI para consultar dados baseados em aba, ano e categoria.
    
    Args:
        id_aba (str): Identificador da aba (e.g., "producao", "comercializacao").
        id_ano (int): Ano da consulta.
        id_categoria (str, optional): Categoria da consulta. Default é None.
    
    Returns:
        json: Os dados processados em formato JSON.
    
    Raises:
        HTTPException: Se os parâmetros fornecidos forem inválidos.
    """
    id_aba = id_aba.lower()
    if id_aba not in ["producao", "comercializacao", "processamento", "importacao", "exportacao"]:
        raise HTTPException(
            status_code = 400,
            detail = "Solicite apenas uma das abas: producao, comercializacao, processamento, importacao, exportacao"
        )
    
    if id_ano < 1970 or id_ano > 2022:
        raise HTTPException(
            status_code = 400, detail = "Solicite apenas dados dos anos entre 1970 e 2022."
        )
    
    if id_categoria is not None and id_aba not in ["producao", "comercializacao"]:
        dict_aux_subcategorias = {
            "processamento": "viniferas, americanas_e_hibridas, uvas_de_mesa, sem_classificacao",
            "importacao": "vinhos_de_mesa, espumante, uvas_frescas, uvas_passas, suco_de_uva",
            "exportacao": "vinhos_de_mesa, espumante, uvas_frescas, suco_de_uva"
        }

        id_categoria = normalize('NFKD', id_categoria).encode('ascii','ignore').decode("ascii").lower()
        if id_categoria not in ["viniferas", "americanas_e_hibridas", "uvas_de_mesa", "sem_classificacao", 
                                "vinhos_de_mesa", "espumante", "uvas_frescas", "uvas_passas", "suco_de_uva"]:
            raise HTTPException(
                status_code = 400, 
                detail = f"Selecione uma das subcategorias abaixo para a aba {id_aba}:{dict_aux_subcategorias[id_aba]}"
            )
        
    return consultar_url(id_aba, id_ano, id_categoria)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)