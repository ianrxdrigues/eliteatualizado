#------------------------------------------------
# Script para Adicionar Usuários ao Banco de Dados no Supabase
#------------------------------------------------
# Este script cria um novo usuário e armazena o hash da senha no Supabase, junto com a data de criação.

from werkzeug.security import generate_password_hash
from datetime import datetime
import os
import sys
from supabase import create_client, Client  # Import para integração com Supabase

# Configuração do Supabase
SUPABASE_URL = "https://yfgfcdxdhrqsuuxbmclt.supabase.co"  # URL do Supabase
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlmZ2ZjZHhkaHJxc3V1eGJtY2x0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIzOTIzMzAsImV4cCI6MjA0Nzk2ODMzMH0.Z_nDP9LhACI7u_AMf8l-I-EMHYQd0o-IBTQf6OZLah0"  # Chave da API do Supabase (substitua pela sua chave)

# Inicializando o cliente do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Verificar se os argumentos foram fornecidos corretamente
if len(sys.argv) < 3:
    print("Uso: python add_user.py <nome_de_usuario> <senha>")
    sys.exit(1)

# Dados do novo usuário obtidos por argumentos de linha de comando
username = sys.argv[1]  # Nome do usuário passado como argumento
password = sys.argv[2]  # Senha do usuário passado como argumento
data_criacao = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # Data e hora atual

# Hash da senha usando um método suportado
hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

# Tentar inserir o usuário no banco de dados do Supabase
try:
    response = supabase.table("usuarios").insert({
        "username": username,
        "password": hashed_password,
        "created_at": data_criacao
    }).execute()

    # Verificar se houve um erro na resposta
    if response.data:
        print(f"Usuário '{username}' adicionado com sucesso.")
    else:
        raise Exception("Erro ao adicionar usuário: " + str(response.error_message))
except Exception as e:
    print(f"Erro ao adicionar usuário '{username}': {e}")
