# Importações necessárias
import logging
import webbrowser
from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import os
import json
import sqlite3
import subprocess
from flask_socketio import SocketIO
from werkzeug.security import generate_password_hash, check_password_hash
from threading import Timer  # Importação necessária para usar o Timer
from supabase import create_client, Client  # Import para integração com Supabase

# Configuração do Supabase
SUPABASE_URL = "https://yfgfcdxdhrqsuuxbmclt.supabase.co"  # URL do Supabase
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InlmZ2ZjZHhkaHJxc3V1eGJtY2x0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzIzOTIzMzAsImV4cCI6MjA0Nzk2ODMzMH0.Z_nDP9LhACI7u_AMf8l-I-EMHYQd0o-IBTQf6OZLah0"  # Chave da API do Supabase (substitua pela sua chave)

# Inicializando o cliente do Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')  # Trocar 'eventlet' por 'gevent' para evitar problemas no empacotamento
app.secret_key = '4e1d2c0a47a6f0a1bc9e9e3b5f6a3a1d5b4e9e3c6a7f8d0b1c5d8f2e9d1c3b7'  # Substitua por uma chave segura

# Configuração do logging para ajudar a identificar erros
logging.basicConfig(level=logging.DEBUG)

# Restante do código...


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
        hashed_password = generate_password_hash(password, method='sha256')

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
            print(f"Resposta da Supabase: {response}")  # Adicione esta linha para depuração

            user = response.data[0] if response.data else None

            if user:
                if check_password_hash(user['password'], password):
                    session['user_id'] = user['uid']  # Corrigi para usar o 'uid' ao invés de 'id'
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
        cookies_data = json.loads(cookies)
        logging.debug(f"Cookies recebidos para o perfil '{nome}': {cookies_data}")
    except json.JSONDecodeError as e:
        logging.error(f"Erro ao decodificar cookies: {e}")
        return jsonify({"error": "Formato inválido dos cookies. Verifique o JSON fornecido."}), 400

    perfil_path = os.path.join(PERFIS_DIR, f"{nome}.json")

    if not cookies_data:
        logging.error("Dados dos cookies estão vazios. Não será salvo.")
        return jsonify({"error": "Os cookies fornecidos estão vazios."}), 400

    try:
        with open(perfil_path, "w") as f:
            json.dump(cookies_data, f, indent=4)
            logging.info(f"Perfil '{nome}' salvo com sucesso.")
    except Exception as e:
        logging.error(f"Erro ao salvar o perfil '{nome}': {e}")
        return jsonify({"error": f"Erro ao salvar o perfil: {str(e)}"}), 500

    return jsonify({"message": f"Perfil {nome} salvo com sucesso!"})

@app.route("/listar_perfis", methods=["GET"])
def listar_perfis():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    perfis = []

    if os.path.exists(PERFIS_DIR):
        for perfil_file in os.listdir(PERFIS_DIR):
            if perfil_file.endswith(".json"):
                perfil_path = os.path.join(PERFIS_DIR, perfil_file)
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

    if os.path.exists(COMENTARIOS_FILE):
        with open(COMENTARIOS_FILE, "r") as f:
            comentarios = json.load(f)
    else:
        comentarios = []

    comentarios.append(comentario)
    with open(COMENTARIOS_FILE, "w") as f:
        json.dump(comentarios, f)

    return jsonify({"message": "Comentário salvo com sucesso!"})

@app.route("/listar_comentarios", methods=["GET"])
def listar_comentarios():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if os.path.exists(COMENTARIOS_FILE):
        with open(COMENTARIOS_FILE, "r") as f:
            comentarios = json.load(f)
    else:
        comentarios = []

    return jsonify(comentarios)

@app.route("/remover_item", methods=["DELETE"])
def remover_item():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    tipo = request.args.get("tipo")
    nome = request.args.get("nome")

    if tipo == "perfil":
        perfil_path = os.path.join(PERFIS_DIR, f"{nome}.json")
        if os.path.exists(perfil_path):
            os.remove(perfil_path)
            return jsonify({"message": f"Perfil '{nome}' removido com sucesso!"})
        else:
            return jsonify({"error": f"Perfil '{nome}' não encontrado."}), 404

    elif tipo == "comentario":
        if os.path.exists(COMENTARIOS_FILE):
            with open(COMENTARIOS_FILE, "r") as f:
                comentarios = json.load(f)

            if nome in comentarios:
                comentarios.remove(nome)
                with open(COMENTARIOS_FILE, "w") as f:
                    json.dump(comentarios, f)

                return jsonify({"message": f"Comentário '{nome}' removido com sucesso!"})
            else:
                return jsonify({"error": f"Comentário '{nome}' não encontrado."}), 404
        else:
            return jsonify({"error": "Arquivo de comentários não encontrado."}), 404

    return jsonify({"error": "Tipo inválido para remoção."}), 400

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

        tarefa = {
            "link": video_url,
            "comentarios": comentarios,
            "perfis": perfis
        }
        tarefa_path = os.path.join(BASE_DIR, "tarefa_temp.json")
        with open(tarefa_path, "w") as f:
            json.dump(tarefa, f)

        def run_automation():
            python_executable = os.path.join(BASE_DIR, 'venv', 'Scripts', 'python.exe')
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

if __name__ == "__main__":
    # Função para abrir o navegador após um pequeno atraso
    def abrir_navegador():
        webbrowser.open("http://127.0.0.1:5000/login")

    # Timer para abrir o navegador após 1 segundo
    Timer(1, abrir_navegador).start()

    # Iniciar o servidor Flask
    socketio.run(app, host="127.0.0.1", port=5000, debug=False)


