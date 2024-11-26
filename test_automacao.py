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
import logging

# Configurar logging para debugar melhor
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        time.sleep(3)

        logger.info(f"Carregando cookies do arquivo: {cookies_file}")
        with open(cookies_file, "r", encoding="utf-8") as file:
            cookies = json.load(file)

            # Verifica se os cookies são uma lista
            if not isinstance(cookies, list):
                raise ValueError("O arquivo de cookies deve conter uma lista de cookies.")

            for cookie in cookies:
                cookie.pop("storeId", None)
                cookie.pop("sameSite", None)
                cookie.pop("hostOnly", None)

                if "domain" not in cookie or not cookie["domain"]:
                    cookie["domain"] = ".tiktok.com"

                driver.add_cookie(cookie)
                logger.info(f"Cookie adicionado: {cookie}")

        driver.get("https://www.tiktok.com")
        time.sleep(3)  # Esperar o carregamento da página

        # Verifica se a página inicial não possui um link de login
        page_source = driver.page_source
        if "Login" in page_source or "Entrar" in page_source or "Sign Up" in page_source:
            raise Exception("Login não detectado. Verifique os cookies fornecidos.")
        else:
            logger.info("Login realizado com sucesso.")
    except ValueError as ve:
        logger.error(f"Erro no formato dos cookies: {ve}")
    except Exception as e:
        logger.error(f"Erro ao carregar cookies do arquivo {cookies_file}: {e}")

def comentar_no_tiktok(driver, url, comentario):
    try_count = 0
    max_retries = 2  # Reduzindo o número de tentativas para acelerar

    while try_count < max_retries:
        try:
            logger.info(f"Acessando a publicação: {url}")
            driver.get(url)

            # Reduzindo tempo de espera para encontrar o campo de comentário
            campo_comentario_container = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[data-e2e="comment-input"]'))
            )

            for _ in range(3):  # Reduzindo o número de rolagens
                driver.execute_script("window.scrollBy(0, 300);")
                time.sleep(random.uniform(0.3, 0.7))

            campo_editavel = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[contenteditable="true"]'))
            )

            ActionChains(driver).move_to_element(campo_editavel).click().perform()
            time.sleep(random.uniform(0.5, 1.0))

            campo_editavel.send_keys(comentario)
            time.sleep(1)
            campo_editavel.send_keys(Keys.RETURN)
            time.sleep(3)

            # Verificar se o comentário está presente na página após ser enviado
            page_source = driver.page_source
            if comentario in page_source:
                logger.info(f"Comentário enviado com sucesso: '{comentario}'")
                break  # Se o comentário foi enviado, sair do loop de tentativas
            else:
                raise Exception("Comentário não encontrado após envio. Tentando novamente...")

        except Exception as e:
            try_count += 1
            logger.error(f"Erro ao enviar comentário (tentativa {try_count}): {str(e)}")
            if try_count >= max_retries:
                logger.error(f"Falha ao enviar o comentário '{comentario}' após {max_retries} tentativas.")
            else:
                time.sleep(5)  # Espera menor antes de tentar novamente
        finally:
            time.sleep(2)

def executar_automacao_por_perfil(perfil, url_publicacao, comentario, progresso_id, total_comentarios):
    try:
        driver = configurar_navegador()
        cookies_file = perfil  # O valor de 'perfil' já contém o caminho completo com a extensão correta
        carregar_cookies(driver, cookies_file)

        comentar_no_tiktok(driver, url_publicacao, comentario)
        
        # Emitir atualização de progresso após cada comentário ser enviado com sucesso
        progresso_atual = (1 / total_comentarios) * 100
        sio.emit('progresso', {'id': progresso_id, 'progresso': progresso_atual})
    except Exception as e:
        logger.error(f"Erro no perfil {perfil}: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()

def processar_lote(lote_perfis, lote_comentarios, url_publicacao, progresso_id, total_comentarios):
    threads = []
    for perfil, comentario in zip(lote_perfis, lote_comentarios):
        thread = Thread(target=executar_automacao_por_perfil, args=(perfil, url_publicacao, comentario, progresso_id, total_comentarios))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

def iniciar_automacao(tarefa_path):
    with open(tarefa_path, "r") as f:
        tarefa = json.load(f)

    url_publicacao = tarefa["link"]
    comentarios = tarefa["comentarios"]
    perfis = tarefa["perfis"]

    total_comentarios = len(perfis)
    progresso_id = random.randint(1000, 9999)  # Gerar um ID único para este ciclo de progresso

    tamanho_lote = 2  # Processar dois perfis por vez para acelerar o processo
    for i in range(0, len(perfis), tamanho_lote):
        lote_perfis = perfis[i:i + tamanho_lote]
        lote_comentarios = comentarios[i:i + tamanho_lote]
        logger.info(f"Processando lote: {lote_perfis} com comentários: {lote_comentarios}")
        processar_lote(lote_perfis, lote_comentarios, url_publicacao, progresso_id, total_comentarios)

    logger.info("Automação finalizada para todos os perfis!")
    sio.emit('progresso', {'id': progresso_id, 'progresso': 100})  # Emitir progresso finalizado

if __name__ == "__main__":
    import sys

    tarefa_path = sys.argv[1]
    iniciar_automacao(tarefa_path)
    sio.disconnect()
