from werkzeug.security import generate_password_hash
import os
import csv
import random
import string
from supabase import create_client, Client

# Configuração do Supabase
SUPABASE_URL = "https://yfgfcdxdhrqsuuxbmclt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlmZ2ZjZHhkaHJxc3V1eGJtY2x0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIzOTIzMzAsImV4cCI6MjA0Nzk2ODMzMH0.Z_nDP9LhACI7u_AMf8l-I-EMHYQd0o-IBTQf6OZLah0"

# Inicializando o cliente do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Diretório para armazenar pastas de dados
DADOS_DIR = "dados"
os.makedirs(DADOS_DIR, exist_ok=True)

def gerar_senha_aleatoria(tamanho=10):
    caracteres = string.ascii_letters + string.digits
    return ''.join(random.choice(caracteres) for _ in range(tamanho))

# Arquivo para salvar as senhas dos usuários
SENHAS_FILE = "senhas_usuarios.csv"

# Criação do arquivo de senhas se não existir
if not os.path.exists(SENHAS_FILE):
    with open(SENHAS_FILE, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["username", "password"])

# Criação de 100 usuários
for i in range(1, 101):
    username = str(i)
    password = gerar_senha_aleatoria()
    hashed_password = generate_password_hash(password, method='pbkdf2:sha256')  # Gerando o hash da senha

    # Tentando registrar o usuário no Supabase
    try:
        response = supabase.table("usuarios").insert({
            "username": username,
            "password": hashed_password  # Salvando a senha como hash
        }).execute()

        # Verifica se a resposta contém dados e se não ocorreu erro
        if response.data:
            print(f"Usuário '{username}' criado com sucesso.")

            # Salvando a senha gerada no arquivo
            with open(SENHAS_FILE, mode='a', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([username, password])  # Salvar a senha em texto simples para referência (não o hash)

            # Criar uma pasta de dados para cada usuário
            user_data_dir = os.path.join(DADOS_DIR, f"usuario_{username}")
            os.makedirs(user_data_dir, exist_ok=True)

        else:
            # Em caso de erro, imprimir a mensagem contida na resposta
            print(f"Erro ao criar usuário '{username}': {response}")

    except Exception as e:
        print(f"Erro ao criar usuário '{username}' no Supabase: {e}")
