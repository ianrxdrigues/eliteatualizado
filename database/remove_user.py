#------------------------------------------------
# Script para Remover Usuários do Banco de Dados
#------------------------------------------------
# Este script remove um usuário específico do banco de dados

import sqlite3
import os
import sys

# Caminho para o banco de dados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, 'comenttspro.db')

# Nome do usuário a ser removido
if len(sys.argv) != 2:
    print("Uso: python remove_user.py <nome_do_usuario>")
    sys.exit(1)

username = sys.argv[1]

# Conectar ao banco de dados
conexao = sqlite3.connect(DATABASE)
cursor = conexao.cursor()

# Remover o usuário se existir
cursor.execute('DELETE FROM usuarios WHERE username = ?', (username,))
conexao.commit()

if cursor.rowcount > 0:
    print(f"Usuário '{username}' removido com sucesso.")
else:
    print(f"Erro: Usuário '{username}' não encontrado.")

# Fechar a conexão
conexao.close()
