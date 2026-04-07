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

@router.post("/video-forge")
async def processar_video_forge(
    voz: UploadFile = File(...),
    legenda: UploadFile = File(...),
    bgm: Optional[UploadFile] = File(None),
    imagens: List[UploadFile] = File(...),
    formato_video: str = Form("vertical"), # <-- NOVO: Recebe o formato do Front
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
        
        # --- A MÁGICA DA LEGENDA E DA ESCALA ACONTECE AQUI ---
        # Definindo a resolução com base no formato escolhido
        if formato_video == "horizontal":
            resolucao_escala = "1920:1080"
            # FontSize 14 em Horizontal é bom, margin de baixo (MarginV) 40
            estilo_leg = "FontName=Arial,FontSize=14,PrimaryColour=&H00FFFF,OutlineColour=&H000000,BorderStyle=3,Bold=-1,Alignment=2,MarginV=40"
        else:
            resolucao_escala = "1080:1920"
            # FontSize 16 em Vertical fica robusto, margin de baixo (MarginV) 120 para não pegar botões do TikTok
            estilo_leg = "FontName=Arial,FontSize=16,PrimaryColour=&H00FFFF,OutlineColour=&H000000,BorderStyle=3,Bold=-1,Alignment=2,MarginV=120"
        
        filtro_legenda = f"subtitles=legenda.srt:force_style='{estilo_leg}'"
        
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", "imagens.txt",
            "-i", "voz.mp3"
        ]
        
        if path_bgm:
            cmd.extend(["-i", "bgm.mp3"])
            cmd.extend([
                "-filter_complex",
                f"[2:a]volume=0.1[bgm_low];[1:a][bgm_low]amix=inputs=2:duration=first[a_mix];[0:v]scale={resolucao_escala}:force_original_aspect_ratio=increase,crop={resolucao_escala},{filtro_legenda}[v_sub]",
                "-map", "[v_sub]", "-map", "[a_mix]"
            ])
        else:
            cmd.extend([
                "-filter_complex",
                f"[0:v]scale={resolucao_escala}:force_original_aspect_ratio=increase,crop={resolucao_escala},{filtro_legenda}[v_sub]",
                "-map", "[v_sub]", "-map", "1:a"
            ])

        cmd.extend(["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", path_saida_absoluto])

        processo = subprocess.run(cmd, cwd=work_dir, capture_output=True, text=True)

        if processo.returncode != 0:
            print("ERRO FFMPEG:", processo.stderr)
            raise Exception("Falha ao renderizar vídeo no FFmpeg.")

        url_video = f"/static/videos/historico/{nome_saida}"
        
        # Histórico Refinado
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
        print(f"❌ Erro no Video Forge: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir)
