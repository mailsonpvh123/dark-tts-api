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
    return "&H00FFFFFF" # Branco fallback

@router.post("/video-forge")
async def processar_video_forge(
    voz: UploadFile = File(...),
    legenda: UploadFile = File(...),
    imagens: List[UploadFile] = File(...),
    bgm: Optional[UploadFile] = File(None),
    watermark: Optional[UploadFile] = File(None),
    formato_video: str = Form("vertical"),
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
        # 1. Salva os arquivos essenciais
        path_voz = os.path.join(work_dir, "voz.mp3")
        with open(path_voz, "wb") as f:
            f.write(await voz.read())
            
        path_srt = os.path.join(work_dir, "legenda.srt")
        with open(path_srt, "wb") as f:
            f.write(await legenda.read())

        # 2. Salva BGM (Opcional)
        path_bgm = None
        if bgm and bgm.filename:
            path_bgm = os.path.join(work_dir, "bgm.mp3")
            with open(path_bgm, "wb") as f:
                f.write(await bgm.read())
                
        # 3. Salva Watermark (Opcional)
        path_wm = None
        if watermark and watermark.filename:
            ext = watermark.filename.split('.')[-1]
            path_wm = os.path.join(work_dir, f"watermark.{ext}")
            with open(path_wm, "wb") as f:
                f.write(await watermark.read())

        audio_voz = AudioSegment.from_file(path_voz)
        duracao_segundos = len(audio_voz) / 1000.0

        tempo_por_img = duracao_segundos / len(imagens) if len(imagens) > 0 else 5.0
        
        path_images_txt = os.path.join(work_dir, "imagens.txt")
        with open(path_images_txt, "w") as f:
            for i, img_file in enumerate(imagens):
                ext = img_file.filename.split(".")[-1]
                img_path = os.path.join(work_dir, f"img_{i}.{ext}")
                with open(img_path, "wb") as f_img:
                    f_img.write(await img_file.read())
                
                f.write(f"file 'img_{i}.{ext}'\n")
                f.write(f"duration {tempo_por_img:.2f}\n")
            
            if imagens:
                ext = imagens[-1].filename.split(".")[-1]
                f.write(f"file 'img_{len(imagens)-1}.{ext}'\n")

        nome_saida = f"videoforge_{usuario.id}_{int(time.time())}.mp4"
        pasta_destino = os.path.join("frontend", "static", "videos", "historico")
        os.makedirs(pasta_destino, exist_ok=True)
        
        path_saida = os.path.join(pasta_destino, nome_saida)
        path_saida_absoluto = os.path.abspath(path_saida)
        
        # ==========================================
        # CONSTRUÇÃO DO COMANDO FFMPEG DINÂMICO
        # ==========================================
        cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", "imagens.txt", "-i", "voz.mp3"]
        
        idx_v_img = 0
        idx_a_voz = 1
        curr_idx = 2
        
        idx_a_bgm = -1
        if path_bgm:
            cmd.extend(["-i", "bgm.mp3"])
            idx_a_bgm = curr_idx
            curr_idx += 1
            
        idx_v_wm = -1
        if path_wm:
            cmd.extend(["-i", f"watermark.{path_wm.split('.')[-1]}"])
            idx_v_wm = curr_idx
            curr_idx += 1

        # Lógica de Legendas
        ass_cor = hex_to_ass_color(cor_legenda)
        ass_contorno = hex_to_ass_color(cor_contorno)
        b_style = "3" if fundo_legenda == "true" else "1"
        align = "8" if posicao_legenda == "top" else ("5" if posicao_legenda == "middle" else "2")
        margin_v = "120" if (formato_video == "vertical" and align == "2") else "40"
        font_size = "14" if formato_video == "horizontal" else "16"
        resolucao_escala = "1920:1080" if formato_video == "horizontal" else "1080:1920"
        
        estilo_leg = f"FontName={fonte_legenda},FontSize={font_size},PrimaryColour={ass_cor},OutlineColour={ass_contorno},BorderStyle={b_style},Bold=-1,Alignment={align},MarginV={margin_v},BackColour=&H66000000"
        filtro_legenda = f"subtitles=legenda.srt:force_style='{estilo_leg}'"

        filter_complex = []
        
        # Audio Mix
        if path_bgm:
            filter_complex.append(f"[{idx_a_bgm}:a]volume=0.1[bgm_low];[{idx_a_voz}:a][bgm_low]amix=inputs=2:duration=first[a_mix]")
            out_a = "[a_mix]"
        else:
            out_a = f"{idx_a_voz}:a"

        # Video Pipeline
        filter_complex.append(f"[{idx_v_img}:v]scale={resolucao_escala}:force_original_aspect_ratio=increase,crop={resolucao_escala}[v_scaled]")
        filter_complex.append(f"[v_scaled]{filtro_legenda}[v_sub]")
        curr_v = "[v_sub]"
        
        # Adiciona Marca D'água por cima de tudo
        if path_wm:
            wm_width = "250" if formato_video == "horizontal" else "150"
            filter_complex.append(f"[{idx_v_wm}:v]scale={wm_width}:-1[wm_scaled]")
            filter_complex.append(f"{curr_v}[wm_scaled]overlay=W-w-30:30[v_out]")
            curr_v = "[v_out]"

        cmd.extend(["-filter_complex", ";".join(filter_complex)])
        cmd.extend(["-map", curr_v, "-map", out_a])
        cmd.extend([
            "-c:v", "libx264", 
            "-crf", "18", 
            "-preset", "slow", 
            "-pix_fmt", "yuv420p", 
            "-sws_flags", "bicubic",
            "-c:a", "aac", 
            "-b:a", "192k", 
            "-t", str(duracao_segundos),
            path_saida_absoluto
        ])

        processo = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)

        if processo.returncode != 0:
            raise Exception(f"Falha técnica na Dark Neural Forge. Tente gerar novamente. Detalhe: {processo.stderr[:50]}")

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
