import json
import time
import os
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from socketio import Client

# Inicializar o cliente SocketIO para comunicar com o servidor
sio = Client()
sio.connect('https://elite-comments-0b755ca4ae3a.herokuapp.com')

def configurar_navegador():
    options = webdriver.ChromeOptions()
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--headless")  # Necessário para rodar sem interface gráfica
    options.add_argument("--no-sandbox")  # Importante para evitar problemas no Heroku
    options.add_argument("--disable-dev-shm-usage")  # Reduz a utilização de memória compartilhada
    options.add_argument("--disable-gpu")  # Desabilita GPU, importante para rodar sem interface gráfica
    options.add_argument("--remote-debugging-port=9222")  # Adiciona suporte para depuração remota
    options.add_argument("--disable-extensions")  # Desativa extensões para evitar falhas
    options.add_argument("--disable-infobars")  # Desativa a barra de informações do Chrome
    options.add_argument("--disable-setuid-sandbox")  # Para evitar problemas de permissões
    options.add_argument("--window-size=1920,1080")  # Define um tamanho fixo para a janela
    options.add_argument("--mute-audio")  # Desativa o áudio para evitar desconforto
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(options=options)
    return driver

def carregar_cookies(driver, cookies_file):
    try:
        driver.get("https://www.tiktok.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        print(f"Carregando cookies do arquivo: {cookies_file}")
        with open(cookies_file, "r", encoding="utf-8") as file:
            cookies = json.load(file)

            if not isinstance(cookies, list):
                raise ValueError("O arquivo de cookies deve conter uma lista de cookies.")

            for cookie in cookies:
                cookie.pop("storeId", None)
                cookie.pop("sameSite", None)
                cookie.pop("hostOnly", None)

                if "domain" not in cookie or not cookie["domain"]:
                    cookie["domain"] = ".tiktok.com"

                driver.add_cookie(cookie)
                print(f"Cookie adicionado: {cookie}")

        driver.get("https://www.tiktok.com")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

        # Verifica se a página inicial não possui um link de login
        page_source = driver.page_source
        if "Login" in page_source or "Entrar" in page_source or "Sign Up" in page_source:
            raise Exception("Login não detectado. Verifique os cookies fornecidos.")
        else:
            print("Login realizado com sucesso.")
    except ValueError as ve:
        print(f"Erro no formato dos cookies: {ve}")
    except Exception as e:
        print(f"Erro ao carregar cookies do arquivo {cookies_file}: {e}")

def comentar_no_tiktok(driver, url, comentario):
    try:
        print(f"Acessando a publicação: {url}")
        driver.get(url)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-e2e="comment-input"]'))
        )

        for _ in range(3):  # Reduzindo o número de scrolls para tornar mais rápido
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(random.uniform(0.3, 0.6))

        campo_editavel = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
        )

        ActionChains(driver).move_to_element(campo_editavel).click().perform()

        for palavra in comentario.split():
            campo_editavel.send_keys(palavra + " ")
            time.sleep(random.uniform(0.1, 0.3))  # Reduzido o tempo entre digitação

        campo_editavel.send_keys(Keys.RETURN)
        WebDriverWait(driver, 10).until(lambda d: comentario in d.page_source)
        print(f"Comentário enviado com sucesso: '{comentario}'")
    except Exception as e:
        print(f"Erro ao enviar comentário: {str(e)}")

def executar_automacao(perfis, url_publicacao, comentarios):
    driver = configurar_navegador()
    try:
        for perfil, comentario in zip(perfis, comentarios):
            carregar_cookies(driver, perfil)
            comentar_no_tiktok(driver, url_publicacao, comentario)
            # Emitir atualização de progresso após cada comentário ser enviado com sucesso
            progresso_atual = (perfis.index(perfil) + 1) / len(perfis) * 100
            sio.emit('progresso', {'id': random.randint(1000, 9999), 'progresso': progresso_atual})
    except Exception as e:
        print(f"Erro durante a automação: {e}")
    finally:
        driver.quit()

def iniciar_automacao(tarefa_path):
    with open(tarefa_path, "r") as f:
        tarefa = json.load(f)

    url_publicacao = tarefa["link"]
    comentarios = tarefa["comentarios"]
    perfis = tarefa["perfis"]

    print(f"Iniciando automação com {len(perfis)} perfis e comentários.")
    executar_automacao(perfis, url_publicacao, comentarios)
    print("Automação finalizada para todos os perfis!")
    sio.emit('progresso', {'id': random.randint(1000, 9999), 'progresso': 100})  # Emitir progresso finalizado

if __name__ == "__main__":
    import sys

    tarefa_path = sys.argv[1]
    iniciar_automacao(tarefa_path)
    sio.disconnect()
