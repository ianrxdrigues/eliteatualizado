#------------------------------------------------
# Script para adicionar a coluna "data_criacao" à tabela "usuarios"
#------------------------------------------------

import sqlite3  # Biblioteca para manipular o SQLite

# Caminho para o banco de dados
DATABASE = 'comenttspro.db'

# Conexão com o banco de dados
conexao = sqlite3.connect(DATABASE)
cursor = conexao.cursor()

# Tenta adicionar a coluna "data_criacao" à tabela "usuarios"
try:
    cursor.execute('ALTER TABLE usuarios ADD COLUMN data_criacao TEXT')
    print("Coluna 'data_criacao' adicionada com sucesso!")
except sqlite3.OperationalError as e:
    print(f"Erro: {e}")

# Fecha a conexão
conexao.close()
