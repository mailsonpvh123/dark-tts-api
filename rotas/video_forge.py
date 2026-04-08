import os
import uuid
import shutil
import subprocess
import time
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from pydub import AudioSegment

import models
from database import get_db
from auth import get_usuario_atual

router = APIRouter(prefix="/api/v1", tags=["Video Forge"])

def hex_to_ass_color(hex_str: str) -> str:
    """Converte HEX HTML (#RRGGBB) para o formato BGR do libass (&H00BBGGRR)"""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r, g, b = hex_str[0:2], hex_str[2:4], hex_str[4:6]
        return f"&H00{b}{g}{r}"
    return "&H00FFFFFF" 

@router.post("/video-forge")
async def processar_video_forge(
    voz: UploadFile = File(...),
    legenda: UploadFile = File(...),
    imagens: List[UploadFile] = File(...),
    bgm: Optional[UploadFile] = File(None),
    watermark: Optional[UploadFile] = File(None),
    formato_video: str = Form("vertical"),
    midia_type: str = Form("imagem"),
    fonte_legenda: str = Form("Arial"),
    cor_legenda: str = Form("#00FFFF"),
    cor_contorno: str = Form("#000000"),
    fundo_legenda: str = Form("false"),
    posicao_legenda: str = Form("bottom"),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_usuario_atual)
):
    if not usuario:
        raise HTTPException(status_code=401, detail="Sessão expirada. Faça login novamente.")

    custo_operacao = 25 

    if usuario.coins < custo_operacao:
        raise HTTPException(status_code=402, detail=f"Coins insuficientes! Necessário {custo_operacao} coins.")
    
    usuario.coins -= custo_operacao
    db.commit()

    id_job = str(uuid.uuid4())[:8]
    work_dir = os.path.join("data", f"forge_{id_job}")
    os.makedirs(work_dir, exist_ok=True)

    try:
        # 1. Salva Arquivos de Base
        path_voz = os.path.join(work_dir, "voz.mp3")
        with open(path_voz, "wb") as f:
            f.write(await voz.read())
            
        path_srt = os.path.join(work_dir, "legenda.srt")
        with open(path_srt, "wb") as f:
            f.write(await legenda.read())

        path_bgm = None
        if bgm and bgm.filename:
            path_bgm = os.path.join(work_dir, "bgm.mp3")
            with open(path_bgm, "wb") as f:
                f.write(await bgm.read())
                
        path_wm = None
        if watermark and watermark.filename:
            ext = watermark.filename.split('.')[-1]
            path_wm = os.path.join(work_dir, f"watermark.{ext}")
            with open(path_wm, "wb") as f:
                f.write(await watermark.read())

        # 2. Leitura Matemática de Tempo
        audio_voz = AudioSegment.from_file(path_voz)
        duracao_segundos = len(audio_voz) / 1000.0

        num_midias = len(imagens)
        tempo_por_midia = duracao_segundos / num_midias if num_midias > 0 else 5.0

        cmd = ["ffmpeg", "-y"]
        
        # 3. Mapeamento de Entradas (A Solução Anti-Congelamento)
        for i, img_file in enumerate(imagens):
            ext = img_file.filename.split(".")[-1]
            img_path = os.path.join(work_dir, f"midia_{i}.{ext}")
            with open(img_path, "wb") as f_img:
                f_img.write(await img_file.read())
            
            # Se imagem: Congela a imagem na tela exatamente pelo tempo fracionado
            if midia_type == "imagem":
                cmd.extend(["-loop", "1", "-t", str(tempo_por_midia), "-i", f"midia_{i}.{ext}"])
            # Se vídeo: Repete o vídeo (caso seja curto) até preencher o tempo fracionado
            else:
                cmd.extend(["-stream_loop", "-1", "-t", str(tempo_por_midia), "-i", f"midia_{i}.{ext}"])

        # Mapeamento do Áudio da Voz
        idx_voz = num_midias
        cmd.extend(["-i", "voz.mp3"])
        
        # Mapeamento BGM
        idx_bgm = -1
        if path_bgm:
            cmd.extend(["-stream_loop", "-1", "-i", "bgm.mp3"])
            idx_bgm = num_midias + 1
            
        # Mapeamento Marca D'água
        idx_wm = -1
        if path_wm:
            ext_wm = path_wm.split('.')[-1]
            cmd.extend(["-i", f"watermark.{ext_wm}"])
            idx_wm = num_midias + 2 if path_bgm else num_midias + 1

        nome_saida = f"videoforge_{usuario.id}_{int(time.time())}.mp4"
        pasta_destino = os.path.join("frontend", "static", "videos", "historico")
        os.makedirs(pasta_destino, exist_ok=True)
        path_saida = os.path.join(pasta_destino, nome_saida)
        path_saida_absoluto = os.path.abspath(path_saida)

        # 4. A Usina de Filtragem (Resolvendo Sincronia de Legenda)
        filter_complex = []
        resolucao_escala = "1920:1080" if formato_video == "horizontal" else "1080:1920"
        
        for i in range(num_midias):
            # Força o vídeo/imagem para o formato exato, com FPS 30 rígido, evitando bugs na legenda
            filter_complex.append(f"[{i}:v]scale={resolucao_escala}:force_original_aspect_ratio=increase,crop={resolucao_escala},fps=30,format=yuv420p,setsar=1[v{i}]")
        
        # Concatena os clipes de forma segura
        concat_str = "".join([f"[v{i}]" for i in range(num_midias)])
        filter_complex.append(f"{concat_str}concat=n={num_midias}:v=1:a=0[v_concat]")
        curr_v = "[v_concat]"
        
        # Formatação Visual da Legenda Exata
        ass_cor = hex_to_ass_color(cor_legenda)
        ass_contorno = hex_to_ass_color(cor_contorno)
        b_style = "3" if fundo_legenda == "true" else "1"
        align = "8" if posicao_legenda == "top" else ("5" if posicao_legenda == "middle" else "2")
        margin_v = "120" if (formato_video == "vertical" and align == "2") else "40"
        font_size = "14" if formato_video == "horizontal" else "16"
        
        estilo_leg = f"FontName={fonte_legenda},FontSize={font_size},PrimaryColour={ass_cor},OutlineColour={ass_contorno},BorderStyle={b_style},Bold=-1,Alignment={align},MarginV={margin_v},BackColour=&H66000000"
        filtro_legenda = f"subtitles=legenda.srt:force_style='{estilo_leg}'"
        
        filter_complex.append(f"{curr_v}{filtro_legenda}[v_sub]")
        curr_v = "[v_sub]"
        
        # Posição da Marca D'água
        if path_wm:
            wm_width = "250" if formato_video == "horizontal" else "150"
            filter_complex.append(f"[{idx_wm}:v]scale={wm_width}:-1[wm_scaled]")
            filter_complex.append(f"{curr_v}[wm_scaled]overlay=W-w-30:30[v_out]")
            curr_v = "[v_out]"
            
        # Ducking do Áudio de Fundo
        if path_bgm:
            filter_complex.append(f"[{idx_bgm}:a]volume=0.1[bgm_low];[{idx_voz}:a][bgm_low]amix=inputs=2:duration=first:dropout_transition=2[a_mix]")
            curr_a = "[a_mix]"
        else:
            curr_a = f"{idx_voz}:a"
            
        cmd.extend(["-filter_complex", ";".join(filter_complex)])
        cmd.extend(["-map", curr_v, "-map", curr_a])
        
        # 5. Aceleração Extrema da Forja
        cmd.extend([
            "-c:v", "libx264", 
            "-preset", "ultrafast", # O segredo para não demorar 1 hora
            "-crf", "23",           # Qualidade limpa sem estourar o tamanho do arquivo
            "-c:a", "aac", 
            "-b:a", "192k", 
            "-t", str(duracao_segundos), # Corta o vídeo magicamente no segundo exato do fim do áudio
            path_saida_absoluto
        ])
        
        processo = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)

        if processo.returncode != 0:
            raise Exception(f"A Forja falhou ao fundir o MP4. Verifique se as imagens são válidas.")

        url_video = f"/static/videos/historico/{nome_saida}"
        
        badge_formato = "📱 Vertical" if formato_video == "vertical" else "📺 Horizontal"
        novo_historico = models.Historico(
            usuario_id=usuario.id,
            ferramenta="Video Forge",
            input_usuario=f"{badge_formato} | {len(imagens)} Cenas | Duração: {duracao_segundos:.1f}s",
            resultado=url_video,
            custo_coins=custo_operacao
        )
        db.add(novo_historico)
        db.commit()

        return {"status": "sucesso", "video_url": url_video, "novo_saldo": usuario.coins}

    except Exception as e:
        usuario.coins += custo_operacao
        db.commit()
        print(f"❌ Erro na Forge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
