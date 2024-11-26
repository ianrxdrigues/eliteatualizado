import logging
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
import json
import sqlite3
import subprocess
import sys
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from supabase import create_client, Client  # Import para integração com Supabase

# Configuração do Supabase usando variáveis de ambiente
SUPABASE_URL = os.getenv("SUPABASE_URL")  # URL do Supabase
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Chave da API do Supabase

# Inicializando o cliente do Supabase
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    raise ValueError("As variáveis SUPABASE_URL e SUPABASE_KEY não estão definidas")

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')  # Substitua por uma chave segura

# Configuração do logging para ajudar a identificar erros
log_level = os.getenv("LOG_LEVEL", "DEBUG")
logging.basicConfig(level=getattr(logging, log_level.upper(), logging.DEBUG))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DADOS_DIR = os.path.join(BASE_DIR, "dados")
PERFIS_DIR = os.path.join(DADOS_DIR, "perfis")
COMENTARIOS_FILE = os.path.join(DADOS_DIR, "comentarios.json")
DATABASE = os.path.join(BASE_DIR, 'database', 'comenttspro.db')

# Cria os diretórios e arquivos necessários
os.makedirs(PERFIS_DIR, exist_ok=True)
if not os.path.exists(COMENTARIOS_FILE):
    with open(COMENTARIOS_FILE, "w") as f:
        json.dump([], f)


# Função auxiliar para acessar o banco de dados
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    if 'user_id' in session:
        return render_template("index.html")
    return redirect(url_for('login'))

# Rota para registrar usuários
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # Tentando registrar o usuário no Supabase
        try:
            response = supabase.table("usuarios").insert({
                "username": username,
                "password": hashed_password
            }).execute()
            logging.info(f"Usuário '{username}' registrado com sucesso no Supabase.")
            return redirect(url_for('login'))
        except Exception as e:
            logging.error(f"Erro ao registrar usuário '{username}' no Supabase: {e}")
            return "Erro ao registrar usuário. Tente outro nome de usuário."

    return render_template('register.html')

# Rota para login de usuários (ATUALIZADA)
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None  # Inicializa a variável de erro como None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Busca o usuário no Supabase
        try:
            response = supabase.table("usuarios").select("*").eq("username", username).execute()
            user = response.data[0] if response.data else None

            if user:
                if check_password_hash(user['password'], password):
                    session['user_id'] = user['username']  # Usar o 'username' como identificador de sessão
                    logging.info(f"Usuário '{username}' logado com sucesso.")
                    return redirect(url_for('index'))
                else:
                    logging.warning(f"Tentativa de login falhou para o usuário '{username}': senha incorreta.")
                    error = "Credenciais inválidas. Tente novamente."
            else:
                logging.warning(f"Tentativa de login falhou para o usuário '{username}': usuário não encontrado.")
                error = "Credenciais inválidas. Tente novamente."
        except Exception as e:
            logging.error(f"Erro ao buscar usuário '{username}' no Supabase: {e}")
            error = "Erro ao tentar fazer login. Tente novamente mais tarde."

    return render_template('login.html', error=error)

# Rota para logout
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route("/salvar_perfil", methods=["POST"])
def salvar_perfil():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    data = request.json
    nome = data.get("nome")
    cookies = data.get("cookies")

    if not nome or not cookies:
        logging.error("Nome do perfil e cookies são obrigatórios.")
        return jsonify({"error": "Nome do perfil e cookies são obrigatórios."}), 400

    try:
        # Limpar o nome do perfil, removendo espaços e caracteres especiais
        nome_limpo = nome.replace(" ", "_")
        cookies_data = json.loads(cookies)
        logging.debug(f"Cookies recebidos para o perfil '{nome_limpo}': {cookies_data}")
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar cookies: {e}")
        return jsonify({"error": "Formato inválido dos cookies. Verifique o JSON fornecido."}), 400

    user_dir = os.path.join(PERFIS_DIR, f"usuario_{session['user_id']}")
    perfil_path = os.path.join(user_dir, f"{nome_limpo}.json")

    if not cookies_data:
        logging.error("Dados dos cookies estão vazios. Não será salvo.")
        return jsonify({"error": "Os cookies fornecidos estão vazios."}), 400

    try:
        os.makedirs(user_dir, exist_ok=True)
        with open(perfil_path, "w") as f:
            json.dump(cookies_data, f, indent=4)
            logging.info(f"Perfil '{nome_limpo}' salvo com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao salvar o perfil '{nome_limpo}': {e}")
        return jsonify({"error": f"Erro ao salvar o perfil: {str(e)}"}), 500

    return jsonify({"message": f"Perfil {nome_limpo} salvo com sucesso!"})

@app.route("/listar_perfis", methods=["GET"])
def listar_perfis():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_dir = os.path.join(PERFIS_DIR, f"usuario_{session['user_id']}")
    perfis = []

    if os.path.exists(user_dir):
        for perfil_file in os.listdir(user_dir):
            # Verifica se o arquivo termina com '.json' e não é 'comentarios.json'
            if perfil_file.endswith(".json") and perfil_file != "comentarios.json":
                perfil_path = os.path.join(user_dir, perfil_file)
                try:
                    with open(perfil_path, "r") as file:
                        conteudo = file.read().strip()
                        if not conteudo:
                            logging.error(f"Erro ao carregar o perfil {perfil_file}: Arquivo está vazio.")
                            continue

                        cookies_list = json.loads(conteudo)

                        perfil_data = {
                            "name": perfil_file.split('.')[0],
                            "cookies": cookies_list
                        }
                        perfis.append(perfil_data)
                except json.JSONDecodeError as e:
                    logging.error(f"Erro ao carregar o perfil {perfil_file}: JSON inválido - {e}")
                    continue
                except Exception as e:
                    logging.error(f"Erro desconhecido ao carregar o perfil {perfil_file}: {e}")
                    continue

    return jsonify(perfis)

@app.route("/salvar_comentario", methods=["POST"])
def salvar_comentario():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    data = request.json
    comentario = data.get("comentario")

    # Definir o caminho da pasta do usuário e do arquivo de comentários
    user_dir = os.path.join(PERFIS_DIR, f"usuario_{session['user_id']}")
    comentarios_file = os.path.join(user_dir, "comentarios.json")

    if not comentario:
        return jsonify({"error": "Comentário não pode estar vazio."}), 400

    # Cria o diretório do usuário se não existir
    os.makedirs(user_dir, exist_ok=True)

    # Carrega os comentários existentes ou cria uma lista vazia se não existir
    if os.path.exists(comentarios_file):
        with open(comentarios_file, "r") as f:
            comentarios = json.load(f)
    else:
        comentarios = []

    # Adiciona o novo comentário e salva no arquivo do usuário
    comentarios.append(comentario)
    with open(comentarios_file, "w") as f:
        json.dump(comentarios, f, indent=4, ensure_ascii=False)

    return jsonify({"message": "Comentário salvo com sucesso!"})

@app.route("/listar_comentarios", methods=["GET"])
def listar_comentarios():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Definir o caminho da pasta do usuário e do arquivo de comentários
    user_dir = os.path.join(PERFIS_DIR, f"usuario_{session['user_id']}")
    comentarios_file = os.path.join(user_dir, "comentarios.json")

    # Carrega os comentários existentes ou cria uma lista vazia se não existir
    if os.path.exists(comentarios_file):
        with open(comentarios_file, "r") as f:
            comentarios = json.load(f)
    else:
        comentarios = []

    return jsonify(comentarios)

import logging

@app.route("/remover_item", methods=["DELETE"])
def remover_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    tipo = request.args.get("tipo")
    nome = request.args.get("nome")

    # Obtém o diretório do usuário logado
    user_dir = os.path.join(PERFIS_DIR, f"usuario_{session['user_id']}")
    logging.debug(f"Diretório do usuário logado: {user_dir}")

    try:
        if tipo == "perfil":
            # Define o caminho do perfil a ser removido
            perfil_path = os.path.join(user_dir, f"{nome}.json")
            logging.debug(f"Caminho do perfil a ser removido: {perfil_path}")

            if os.path.exists(perfil_path):
                os.remove(perfil_path)
                logging.info(f"Perfil '{nome}' removido com sucesso!")
                return jsonify({"message": f"Perfil '{nome}' removido com sucesso!"})
            else:
                logging.error(f"Perfil '{nome}' não encontrado no caminho '{perfil_path}'.")
                return jsonify({"error": f"Perfil '{nome}' não encontrado."}), 404

        elif tipo == "comentario":
            comentarios_file = os.path.join(user_dir, "comentarios.json")
            logging.debug(f"Caminho do arquivo de comentários: {comentarios_file}")

            if os.path.exists(comentarios_file):
                with open(comentarios_file, "r") as f:
                    comentarios = json.load(f)

                if nome in comentarios:
                    comentarios.remove(nome)
                    with open(comentarios_file, "w") as f:
                        json.dump(comentarios, f)
                    logging.info(f"Comentário '{nome}' removido com sucesso!")
                    return jsonify({"message": f"Comentário '{nome}' removido com sucesso!"})
                else:
                    logging.error(f"Comentário '{nome}' não encontrado no arquivo de comentários.")
                    return jsonify({"error": f"Comentário '{nome}' não encontrado."}), 404
            else:
                logging.error(f"Arquivo de comentários não encontrado no caminho '{comentarios_file}'.")
                return jsonify({"error": "Arquivo de comentários não encontrado."}), 404

        else:
            logging.error("Tipo inválido para remoção: " + str(tipo))
            return jsonify({"error": "Tipo inválido para remoção."}), 400

    except Exception as e:
        logging.error(f"Erro ao remover o item '{nome}' do tipo '{tipo}': {e}")
        return jsonify({"error": f"Erro ao remover o item: {str(e)}"}), 500



@app.route("/enviar_comentarios", methods=["POST"])
def enviar_comentarios():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        data = request.json
        video_url = data.get("videoUrl")
        perfis = data.get("perfis")
        comentarios = data.get("comentarios")

        if not video_url or not perfis or not comentarios:
            logging.error("Dados incompletos para enviar comentários.")
            return jsonify({"error": "Dados incompletos para enviar comentários."}), 400

        # Atualiza o caminho para os perfis baseado no usuário logado
        user_id = session['user_id']
        user_dir = os.path.join(PERFIS_DIR, f"usuario_{user_id}")

        # Corrigir o caminho dos perfis, evitando duplicação do ".json"
        perfis_paths = []
        for perfil in perfis:
           perfil_path = os.path.join(user_dir, f"{perfil}.json")
           perfis_paths.append(perfil_path)


        # Atualiza o objeto de tarefa com os caminhos corrigidos dos perfis
        tarefa = {
            "link": video_url,
            "comentarios": comentarios,
            "perfis": perfis_paths
        }

        # Criar um arquivo de tarefa único para cada usuário
        tarefa_path = os.path.join(BASE_DIR, f"tarefa_temp_{user_id}.json")
        with open(tarefa_path, "w") as f:
            json.dump(tarefa, f)

        def run_automation():
            python_executable = sys.executable
            script_path = os.path.join(BASE_DIR, "test_automacao.py")
            logging.info(f"Executando o script de automação com o comando: {python_executable} {script_path} {tarefa_path}")

            result = subprocess.run(
                [python_executable, script_path, tarefa_path], 
                capture_output=True, 
                text=True
            )

            if result.stdout:
                logging.info(f"Saída do script de automação (stdout): {result.stdout}")
            else:
                logging.info("Saída do script de automação (stdout) está vazia.")

            if result.stderr:
                logging.error(f"Erros do script de automação (stderr): {result.stderr}")
            else:
                logging.info("Erros do script de automação (stderr) estão vazios.")

            if result.returncode != 0:
                logging.error(f"Erro ao executar o script de automação. Código de retorno: {result.returncode}")
                socketio.emit('progress_update', {'status': 'error', 'message': 'Erro ao executar a automação'})
            else:
                socketio.emit('progress_update', {'status': 'complete', 'message': 'Comentários enviados com sucesso!'})

        # Emita um evento de progresso inicial
        socketio.emit('progress_update', {'status': 'in_progress', 'message': 'Iniciando a automação, aguarde!'})

        # Iniciar a automação em uma thread separada
        socketio.start_background_task(run_automation)

        return jsonify({"message": "Processo de automação iniciado. Avisaremos assim que for concluído."})

    except Exception as e:
        logging.exception("Ocorreu um erro inesperado ao tentar enviar comentários.")
        return jsonify({"error": str(e)}), 500


    except Exception as e:
        logging.exception("Ocorreu um erro inesperado ao tentar enviar comentários.")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        logging.exception("Ocorreu um erro inesperado ao tentar enviar comentários.")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        logging.exception("Ocorreu um erro inesperado ao tentar enviar comentários.")
        return jsonify({"error": str(e)}), 500

    except Exception as e:
        logging.exception("Ocorreu um erro inesperado ao tentar enviar comentários.")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
