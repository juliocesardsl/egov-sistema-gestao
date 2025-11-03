# salvar como: database_manager.py
import sqlite3
import os
import sys

def get_app_path(relative_path):
    """ Retorna o caminho para um arquivo na pasta do aplicativo (ou script). """
    if getattr(sys, 'frozen', False):
        # Se estiver rodando como um executável (PyInstaller)
        base_path = os.path.dirname(sys.executable)
    else:
        # Se estiver rodando como um script .py
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def get_db_path():
    """Retorna o caminho completo para o arquivo do banco de dados."""
    return get_app_path('banco.db')

def execute_query(query, params=(), fetch=None):
    """
    Executa uma consulta no banco de dados de forma segura.

    Args:
        query (str): A string da consulta SQL.
        params (tuple): Os parâmetros para a consulta.
        fetch (str, optional): O tipo de busca a ser feita. 
                               'one' para fetchone, 'all' para fetchall.
                               None para operações de escrita (INSERT, UPDATE, DELETE).

    Returns:
        Resultado da consulta (se fetch for 'one' ou 'all'), ou None.
    """
    try:
        # O timeout ajuda a evitar erros de 'database is locked' em operações rápidas e concorrentes
        with sqlite3.connect(get_db_path(), timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)

            if fetch == 'one':
                result = cursor.fetchone()
            elif fetch == 'all':
                result = cursor.fetchall()
            else:
                conn.commit() # Confirma a transação para operações de escrita
                result = None
            
            return result
    except sqlite3.Error as e:
        print(f"ERRO DE BANCO DE DADOS: {e}")
        print(f"  - Query: {query}")
        return None # Ou poderia levantar a exceção: raise e