#------------------------------------------------
# Script para Criar a Tabela de Usuários no Banco de Dados
#------------------------------------------------
# Este script cria a tabela 'usuarios' no banco de dados 'comenttspro.db',
# contendo as colunas 'username', 'password' e 'data_criacao'.

import sqlite3
import os

# Caminho para o banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'comenttspro.db')

# Conectar ao banco de dados
conexao = sqlite3.connect(DATABASE)
cursor = conexao.cursor()

# Criação da tabela de usuários (se não existir)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password TEXT NOT NULL,
        data_criacao TEXT NOT NULL
    )
''')

# Confirmar a criação da tabela
conexao.commit()
print("Tabela 'usuarios' criada com sucesso (se já não existia).")

# Fechar a conexão
conexao.close()
