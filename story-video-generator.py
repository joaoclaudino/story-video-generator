# -*- coding: utf-8 -*-
import requests
import openai
import os
import json
from datetime import datetime
import time
import re
from gtts import gTTS
import pyttsx3
from moviepy.editor import *
import textwrap
from moviepy.config import change_settings
change_settings({"IMAGEMAGICK_BINARY": r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe"})

# Função para carregar configurações do arquivo JSON
def carregar_configuracao():
    print("[INFO] Carregando configurações...")
    with open("config.json", "r", encoding="utf-8") as arquivo:
        configuracao = json.load(arquivo)
    print("[INFO] Configurações carregadas com sucesso.")
    return configuracao

# Carregar configurações do arquivo JSON e definir a chave de API
config = carregar_configuracao()
openai.api_key = config["openai_api_key"]

def criar_diretorio_execucao(numero_de_prompts):
    data_hora = datetime.now().strftime("%Y%m%d_%H%M%S")
    pasta_base = os.path.join("output", f"execucao_{data_hora}_prompts_{numero_de_prompts}")
    os.makedirs(pasta_base)
    print(f"[INFO] Diretório principal criado: {pasta_base}")
    return pasta_base

def gerar_prompts(numero_de_prompts, pasta_base):
    prompt_gerador = (
        f"Crie uma lista de {numero_de_prompts} ideias de histórias infantis únicas e criativas para vídeos curtos. "
        "Cada história deve começar com o número, ponto e o título na mesma linha, seguido por uma nova linha com a descrição. "
        "Por exemplo:\n\n"
        "1. Título da História\nDescrição detalhada da história..."
    )

    print("[INFO] Gerando prompts de histórias...")
    inicio = time.time()
    
    resposta = openai.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "user", "content": prompt_gerador}
        ],
        max_tokens=config["max_tokens_prompt"],
        temperature=config["temperature"]
    )

    resposta_texto = resposta.choices[0].message.content.strip()
    prompts_gerados = re.findall(r'\d+\.\s([^\n]+)\n([^\n]+(?:\n[^\d.]+)*)', resposta_texto)
    prompts_formatados = [f"{titulo.strip()}\n{descricao.strip()}" for titulo, descricao in prompts_gerados]
    
    fim = time.time()
    print(f"[INFO] {len(prompts_formatados)} prompts gerados em {fim - inicio:.2f} segundos.")
    
    # Salvar o prompt enviado e os títulos gerados
    caminho_prompt_envio = os.path.join(pasta_base, "prompt_enviado.txt")
    caminho_titulos_recebidos = os.path.join(pasta_base, "titulos_recebidos.txt")
    
    with open(caminho_prompt_envio, "w", encoding="utf-8") as arquivo:
        arquivo.write(prompt_gerador)
    print(f"[INFO] Prompt enviado salvo em {caminho_prompt_envio}")
    
    with open(caminho_titulos_recebidos, "w", encoding="utf-8") as arquivo:
        arquivo.write("\n\n".join(prompts_formatados))
    print(f"[INFO] Títulos recebidos salvos em {caminho_titulos_recebidos}")
    
    return prompts_formatados

def gerar_historia(prompt):
    print(f"[INFO] Gerando história para o prompt: '{prompt[:30]}...'")
    inicio = time.time()
 
    prompt_com_acao = (
        f"{prompt}\n\n"
    )

    resposta = openai.chat.completions.create(
        model=config["model"],
        messages=[
            {"role": "user", "content": prompt_com_acao}
        ],
        max_tokens=config["max_tokens_historia"],
        temperature=config["temperature"]
    )
    
    fim = time.time()
    print(f"[INFO] História gerada em {fim - inicio:.2f} segundos.")
    return resposta.choices[0].message.content.strip()

def gerar_ilustracoes(prompt_ilustracao, pasta_imagens, num_imagens=3):
    print(f"[INFO] Gerando {num_imagens} ilustrações para o prompt: '{prompt_ilustracao[:30]}...'")
    inicio = time.time()
    
    try:
        for i in range(1, num_imagens + 1):            
            resposta = openai.images.generate(
                    model= "dall-e-3",
                    prompt= prompt_ilustracao,
                    n= 1,
                    size= "1024x1024"
                  );
            
            imagem_url =  resposta.data[0].url
            caminho_imagem = os.path.join(pasta_imagens, f"ilustracao_{i}.png")
            
            # Usar requests para baixar e salvar a imagem
            img_data = requests.get(imagem_url).content
            with open(caminho_imagem, "wb") as img_file:
                img_file.write(img_data)
            
            print(f"[INFO] Ilustração {i} salva em {caminho_imagem}")
        
    except Exception as e:
        print(f"[ERROR] Falha ao gerar as ilustrações: {e}")
    
    fim = time.time()
    print(f"[INFO] {num_imagens} ilustrações geradas em {fim - inicio:.2f} segundos.")

def salvar_prompts_e_historias(pasta_base, prompts_gerados):
    for i, prompt in enumerate(prompts_gerados, start=1):
        partes_prompt = prompt.split("\n", 1)
        titulo = partes_prompt[0].strip()
        historia_prompt = partes_prompt[1].strip() if len(partes_prompt) > 1 else ""
        historia_prompt = f"{config['parametros_geracao_historia']}{historia_prompt}"
        titulo_limpo = re.sub(r'[\\/*?:"<>|]', "", titulo[:50]).strip()
        pasta_titulo = os.path.join(pasta_base, titulo_limpo)
        os.makedirs(pasta_titulo, exist_ok=True)
        
        # Criar subpasta para imagens dentro da pasta da história
        pasta_imagens = os.path.join(pasta_titulo, "imagens")
        os.makedirs(pasta_imagens, exist_ok=True)
        
        # Salvar o prompt da história
        caminho_prompt = os.path.join(pasta_titulo, "prompt.txt")
        with open(caminho_prompt, "w", encoding="utf-8") as arquivo:
            arquivo.write(historia_prompt)
        print(f"[INFO] Prompt salvo em {caminho_prompt}")

        # Gerar a história e salvar o texto
        historia_prompt= (
            f"{historia_prompt}"
            "No inicio da história, inclua uma o Título da História.Mas sem falar a palavra Título!!!\n\n"
            "Comece o video falando o Título!!!\n\n"
            "No final da história, inclua uma mensagem pedindo ao público para seguir o canal para mais histórias, exemplo: Gostou da história? Siga nosso canal para mais contos incríveis e compartilhe com seus amigos! Deixa um Like no Vídeo"
        )
        historia = gerar_historia(historia_prompt)
        caminho_historia = os.path.join(pasta_titulo, f"{titulo_limpo}.txt")
        
        with open(caminho_historia, "w", encoding="utf-8") as arquivo:
            arquivo.write(historia)
        print(f"[INFO] História salva em {caminho_historia}")
        
        # Gerar o prompt de ilustração e salvar em um arquivo texto
        prompt_ilustracao = f"Ilustração infantil para: {titulo}. {historia_prompt[:150]}... Cores suaves, estilo amigável para crianças. Caso exista, o Texto das imagens deve ser em Português"
        caminho_prompt_ilustracao = os.path.join(pasta_titulo, "prompt_ilustracao.txt")
        
        with open(caminho_prompt_ilustracao, "w", encoding="utf-8") as arquivo:
            arquivo.write(prompt_ilustracao)
        print(f"[INFO] Prompt de ilustração salvo em {caminho_prompt_ilustracao}")
        
        # Gerar a ilustração e salvar na subpasta de imagens
        gerar_ilustracoes(prompt_ilustracao, pasta_imagens,2)

        # Gerar a narração da história e salvar o arquivo de áudio
        gerar_narracao_pyttsx3(historia, pasta_titulo)  # Use `gerar_narracao_pyttsx3` se preferir o TTS offline
        gerar_narracao_gtts(historia, pasta_titulo)  # Use `gerar_narracao_pyttsx3` se preferir o TTS offline
        montar_video_com_legendas(pasta_titulo)

def montar_video_com_legendas(pasta_titulo):
    print(f"[INFO] Montando o vídeo com legendas para a história na pasta: {pasta_titulo}")
    
    # Caminho das imagens e áudio gerados
    pasta_imagens = os.path.join(pasta_titulo, "imagens")
    audio_gtts = os.path.join(pasta_titulo, "narracaogtts.mp3")
    audio_pyttsx3 = os.path.join(pasta_titulo, "narracaopyttsx3.wav")
    
    # Selecionar o áudio desejado (gTTS ou pyttsx3)
    caminho_audio = audio_gtts if os.path.exists(audio_gtts) else audio_pyttsx3
    if not os.path.exists(caminho_audio):
        print("[ERROR] Arquivo de áudio não encontrado!")
        return
    
    # Carregar o áudio e definir a duração
    audio = AudioFileClip(caminho_audio)
    duracao_audio = audio.duration
    
    # Carregar o texto da história
    caminho_historia = os.path.join(pasta_titulo, f"{os.path.basename(pasta_titulo)}.txt")
    with open(caminho_historia, "r", encoding="utf-8") as arquivo:
        historia_texto = arquivo.read()
    
    # Dividir a história em trechos curtos para cada imagem
    imagens = sorted([os.path.join(pasta_imagens, img) for img in os.listdir(pasta_imagens) if img.endswith(".png")])
    duracao_por_imagem = duracao_audio / len(imagens) if imagens else 1
    trechos_texto = textwrap.wrap(historia_texto, width=60)  # Ajuste o width conforme necessário
    
    # Ajustar imagens para o formato 9:16, adicionar legendas e aplicar transições
    clipes_imagens = []
    for i, img in enumerate(imagens):
        # Reduzir a resolução para acelerar a renderização
        clip = ImageClip(img).resize(height=1280, width=720).set_duration(duracao_por_imagem)
        
        # Centralizar a imagem no formato vertical 9:16 com fundo branco
        clip = clip.set_position("center").on_color(
            size=(1080, 1920), color=(255, 255, 255), col_opacity=1
        )
        
        # Adicionar uma legenda se houver um trecho correspondente
        if i < len(trechos_texto):
            texto_legenda = trechos_texto[i]
            legenda = TextClip(texto_legenda, fontsize=50, color='black', font="Arial-Bold")
            legenda = legenda.set_position(("center", 1600)).set_duration(duracao_por_imagem)  # Ajusta a posição vertical
            clip = CompositeVideoClip([clip, legenda])  # Combina a imagem com a legenda
        
        # Adicionar transição suave (crossfade)
        clip = clip.crossfadein(1)
        clipes_imagens.append(clip)
    
    # Concatenar os clipes de imagens com legendas e transições
    video = concatenate_videoclips(clipes_imagens, method="compose")
    video = video.set_audio(audio)  # Adicionar o áudio ao vídeo
    
    # Salvar o vídeo final com todas as otimizações de performance
    caminho_video = os.path.join(pasta_titulo, "video_final_com_legendas.mp4")
    video.write_videofile(
        caminho_video,
        fps=15,                    # Diminui o fps para 15 para renderização mais rápida
        codec="libx264",           # Codec otimizado
        audio_codec="aac",
        threads=8,                 # Usa múltiplos threads para processamento paralelo
        preset="ultrafast"         # Usa preset de renderização rápido
    )
    print(f"[INFO] Vídeo final com legendas salvo em {caminho_video}")

def gerar_narracao_gtts(texto, pasta_titulo, nome_arquivo="narracaogtts.mp3"):
    caminho_audio = os.path.join(pasta_titulo, nome_arquivo)
    print(f"[INFO] Gerando narração para a história...")

    try:
        tts = gTTS(text=texto, lang="pt-br", slow=False, tld="com.br")
        tts.save(caminho_audio)
        print(f"[INFO] Narração salva em {caminho_audio}")
    except Exception as e:
        print(f"[ERROR] Falha ao gerar a narração: {e}")

    return caminho_audio
def gerar_narracao_pyttsx3(texto, pasta_titulo, nome_arquivo="narracaopyttsx3.wav"):
    caminho_audio = os.path.join(pasta_titulo, nome_arquivo)
    print(f"[INFO] Gerando narração para a história...")

    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 150)  # Velocidade da fala
        engine.setProperty('volume', 1)  # Volume da fala

        # Seleciona uma voz em português
        voices = engine.getProperty('voices')
        for voice in voices:
            if "pt" in voice.languages:
                engine.setProperty('voice', voice.id)
                break

        engine.save_to_file(texto, caminho_audio)
        engine.runAndWait()
        print(f"[INFO] Narração salva em {caminho_audio}")
    except Exception as e:
        print(f"[ERROR] Falha ao gerar a narração: {e}")

    return caminho_audio

def main():
    print("[INFO] Iniciando o processo...")
    tempo_inicio = time.time()
    
    if not os.path.exists("output"):
        os.makedirs("output")
        print("[INFO] Diretório 'output' criado.")
    
    numero_de_prompts = config["numero_de_prompts"]
    pasta_base = criar_diretorio_execucao(numero_de_prompts)
    
    prompts_gerados = gerar_prompts(numero_de_prompts, pasta_base)
    salvar_prompts_e_historias(pasta_base, prompts_gerados)
    
    tempo_fim = time.time()
    print(f"[INFO] Processo concluído! Tempo total de execução: {tempo_fim - tempo_inicio:.2f} segundos.")
    print(f"[INFO] Diretório base dos resultados: {pasta_base}")

# Executar o script principal
main()
