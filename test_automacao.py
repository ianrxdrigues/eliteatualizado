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
from threading import Thread
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
    options.add_argument("--disable-extensions")  # Desativa extensões para evitar falhas
    options.add_argument("--disable-infobars")  # Desativa a barra de informações do Chrome
    options.add_argument("--window-size=1920,1080")  # Define um tamanho fixo para a janela
    options.add_argument("--mute-audio")  # Desativa o áudio para evitar desconforto

    driver = webdriver.Chrome(options=options)
    return driver

def carregar_cookies(driver, cookies_file):
    try:
        driver.get("https://www.tiktok.com")
        time.sleep(3)  # Reduzi de 5 para 3 segundos

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
        time.sleep(3)  # Espera o carregamento da página

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
    try_count = 0
    max_retries = 2  # Reduzi de 3 para 2 tentativas

    while try_count < max_retries:
        try:
            print(f"Acessando a publicação: {url}")
            driver.get(url)

            # Pequena rolagem para garantir o carregamento da página
            for _ in range(3):  # Reduzi de 5 para 3 rolamentos
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(random.uniform(0.3, 0.7))

            campo_editavel = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
            )

            ActionChains(driver).move_to_element(campo_editavel).click().perform()
            time.sleep(random.uniform(0.5, 1.0))  # Reduzi o tempo de espera

            for palavra in comentario.split():
                campo_editavel.send_keys(palavra + " ")
                time.sleep(random.uniform(0.2, 0.5))  # Reduzi o tempo de espera

            campo_editavel.send_keys(Keys.RETURN)
            time.sleep(3)  # Reduzi de 5 para 3 segundos

            # Verificar se o comentário está presente na página após ser enviado
            page_source = driver.page_source
            if comentario in page_source:
                print(f"Comentário enviado com sucesso: '{comentario}'")
                break
            else:
                raise Exception("Comentário não encontrado após envio. Tentando novamente...")

        except Exception as e:
            try_count += 1
            print(f"Erro ao enviar comentário (tentativa {try_count}): {str(e)}")
            if try_count >= max_retries:
                print(f"Falha ao enviar o comentário '{comentario}' após {max_retries} tentativas.")
            else:
                time.sleep(5)  # Espera menor antes de tentar novamente
        finally:
            time.sleep(3)

def executar_automacao_por_perfil(perfil, url_publicacao, comentario, progresso_id, total_comentarios):
    driver = None
    try:
        driver = configurar_navegador()
        cookies_file = perfil
        carregar_cookies(driver, cookies_file)

        comentar_no_tiktok(driver, url_publicacao, comentario)
        
        progresso_atual = (1 / total_comentarios) * 100
        sio.emit('progresso', {'id': progresso_id, 'progresso': progresso_atual})
    except Exception as e:
        print(f"Erro no perfil {perfil}: {e}")
    finally:
        if driver:
            driver.quit()

def processar_lote(lote_perfis, lote_comentarios, url_publicacao, progresso_id, total_comentarios):
    for perfil, comentario in zip(lote_perfis, lote_comentarios):
        executar_automacao_por_perfil(perfil, url_publicacao, comentario, progresso_id, total_comentarios)

def iniciar_automacao(tarefa_path):
    with open(tarefa_path, "r") as f:
        tarefa = json.load(f)

    url_publicacao = tarefa["link"]
    comentarios = tarefa["comentarios"]
    perfis = tarefa["perfis"]

    total_comentarios = len(perfis)
    progresso_id = random.randint(1000, 9999)

    tamanho_lote = 1  # Processar um perfil por vez para reduzir sobrecarga
    for i in range(0, len(perfis), tamanho_lote):
        lote_perfis = perfis[i:i + tamanho_lote]
        lote_comentarios = comentarios[i:i + tamanho_lote]
        print(f"Processando lote: {lote_perfis} com comentários: {lote_comentarios}")
        processar_lote(lote_perfis, lote_comentarios, url_publicacao, progresso_id, total_comentarios)

    print("Automação finalizada para todos os perfis!")
    sio.emit('progresso', {'id': progresso_id, 'progresso': 100})

if __name__ == "__main__":
    import sys

    tarefa_path = sys.argv[1]
    iniciar_automacao(tarefa_path)
    sio.disconnect()
