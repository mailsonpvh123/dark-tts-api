// ==========================================
// CONFIGURAÇÕES GLOBAIS
// ==========================================
const URL_API_VOZES = "/vozes"; 
const URL_API_DIRETA = "/gerar_narracao"; 
let vozesData = [];
let vozSelecionada = "padrao-pt-BR-AntonioNeural"; 
let srtGlobal = ""; 
let timerDebounceCusto = null; 
let abaVozAtiva = "padrao";

// Estado do Histórico
let histPaginaAtual = 1;
let histFiltroAtual = "";
let histLimite = 10;
let histDadosAtuais = []; 

// ==========================================
// INICIALIZAÇÃO DA PLATAFORMA
// ==========================================
document.addEventListener('DOMContentLoaded', async function() {
    const path = window.location.pathname;
    
    document.querySelectorAll('.menu-btn').forEach(link => {
        if (link.getAttribute('href') === path) {
            link.classList.add('text-white', 'bg-zinc-800/80', 'border-zinc-700');
            link.classList.remove('text-zinc-400');
            const icon = link.querySelector('i');
            if (path === '/gen-insights') icon.classList.add('text-yellow-400');
            if (path === '/miner') icon.classList.add('text-indigo-400');
            if (path === '/paraphraser') icon.classList.add('text-pink-400');
            if (path === '/script-forge') icon.classList.add('text-orange-400');
            if (path === '/voice-synthesizer') icon.classList.add('text-purple-400');
            if (path === '/scenemaker') icon.classList.add('text-cyan-400');
            if (path === '/video-forge') icon.classList.add('text-indigo-400');
            if (path === '/meta-seo') icon.classList.add('text-blue-400');
            if (path === '/thumb-maker') icon.classList.add('text-pink-400');
            if (path === '/clip-hunter') icon.classList.add('text-emerald-400');
            if (path === '/historico') icon.classList.add('text-emerald-400');
        }
    });

    if (path === '/historico') {
        carregarHistorico();
    }

    const textoVoice = localStorage.getItem('texto_pendente_voice');
    if (textoVoice && document.getElementById('texto_voz')) {
        document.getElementById('texto_voz').value = textoVoice;
        localStorage.removeItem('texto_pendente_voice');
        if(typeof recalcularCustoVoz === 'function') recalcularCustoVoz();
    }

    if(document.getElementById('lista_vozes')) {
        try {
            const resposta = await fetch(URL_API_VOZES);
            if (!resposta.ok) throw new Error("Falha ao comunicar com a API.");
            const dados = await resposta.json();
            if(dados.status === "erro") throw new Error(dados.mensagem);
            
            vozesData = dados.vozes || dados;
            alternarAbaVozes('padrao'); 
        } catch (error) { 
            console.log("Erro TTS:", error);
            document.getElementById('lista_vozes').innerHTML = `
                <div class="text-center text-red-500 py-10">
                    <i class="fa-solid fa-triangle-exclamation text-3xl mb-3 drop-shadow-[0_0_10px_rgba(239,68,68,0.5)]"></i>
                    <br><span class="text-sm font-bold">Erro de Conexão com o Estúdio</span>
                </div>`;
        }
    }
});

// ==========================================
// FUNÇÕES DO HISTÓRICO
// ==========================================
async function carregarHistorico() {
    const tabela = document.getElementById('tabela_historico');
    tabela.innerHTML = `<div class="p-8 text-center text-zinc-500 font-bold"><i class="fa-solid fa-circle-notch fa-spin mr-2"></i> Carregando registros da base de dados...</div>`;
    
    try {
        let url = `/api/v1/historico?pagina=${histPaginaAtual}&limite=${histLimite}`;
        if (histFiltroAtual) {
            url += `&ferramenta=${encodeURIComponent(histFiltroAtual)}`;
        }

        const response = await fetch(url);
        if (!response.ok) throw new Error("Falha ao buscar histórico");
        const data = await response.json();
        
        histDadosAtuais = data.historico; 
        
        tabela.innerHTML = "";
        
        if (histDadosAtuais.length === 0) {
            tabela.innerHTML = `<div class="p-10 text-center"><p class="text-zinc-500 font-bold text-sm">Nenhum registro encontrado.</p></div>`;
        } else {
            histDadosAtuais.forEach((h, index) => {
                let cor = 'text-zinc-400';
                let icone = 'fa-code';
                let bgIcone = 'bg-zinc-800';
                
                if(h.ferramenta.includes("Voice")) { cor = 'text-purple-400'; icone = 'fa-microphone-lines'; bgIcone = 'bg-purple-500/10 border-purple-500/30 text-purple-400';}
                else if(h.ferramenta.includes("Script")) { cor = 'text-orange-400'; icone = 'fa-pen-nib'; bgIcone = 'bg-orange-500/10 border-orange-500/30 text-orange-400';}
                else if(h.ferramenta.includes("Meta")) { cor = 'text-blue-400'; icone = 'fa-magnifying-glass-chart'; bgIcone = 'bg-blue-500/10 border-blue-500/30 text-blue-400';}
                else if(h.ferramenta.includes("Thumb")) { cor = 'text-rose-400'; icone = 'fa-image'; bgIcone = 'bg-rose-500/10 border-rose-500/30 text-rose-400';}
                else if(h.ferramenta.includes("Gen")) { cor = 'text-yellow-400'; icone = 'fa-lightbulb'; bgIcone = 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400';}
                else if(h.ferramenta.includes("Miner")) { cor = 'text-indigo-400'; icone = 'fa-magnet'; bgIcone = 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400';}
                else if(h.ferramenta.includes("Paraph")) { cor = 'text-pink-400'; icone = 'fa-rotate'; bgIcone = 'bg-pink-500/10 border-pink-500/30 text-pink-400';}
                else if(h.ferramenta.includes("Scene")) { cor = 'text-cyan-400'; icone = 'fa-clapperboard'; bgIcone = 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400';}
                else if(h.ferramenta.includes("Video Forge")) { cor = 'text-indigo-400'; icone = 'fa-hammer'; bgIcone = 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400';}

                let inputCurto = h.input_usuario.length > 50 ? h.input_usuario.substring(0, 50) + '...' : h.input_usuario;

                tabela.innerHTML += `
                    <div class="grid grid-cols-1 md:grid-cols-12 gap-4 p-4 hover:bg-zinc-800/30 transition-colors items-center border-b border-zinc-800/30 last:border-0">
                        <div class="col-span-2 text-xs font-mono text-zinc-500"><i class="fa-regular fa-calendar-days mr-1"></i> ${h.data_formatada}</div>
                        <div class="col-span-3 font-semibold text-sm flex items-center gap-2">
                            <span class="w-6 h-6 rounded flex items-center justify-center border ${bgIcone} text-[10px]"><i class="fa-solid ${icone}"></i></span>
                            <span class="${cor}">${h.ferramenta}</span>
                        </div>
                        <div class="col-span-4 text-xs text-zinc-400 italic truncate" title="${h.input_usuario}">"${inputCurto}"</div>
                        <div class="col-span-1 text-center font-mono text-xs text-emerald-500 font-bold"><i class="fa-solid fa-coins mr-1 text-emerald-400"></i>${h.custo_coins}</div>
                        <div class="col-span-2 text-right flex items-center justify-end gap-2">
                            <button onclick="abrirModal(${index})" class="px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-emerald-600 text-zinc-300 hover:text-white font-bold text-[11px] transition-colors border border-zinc-700 flex items-center gap-1">
                                <i class="fa-solid fa-eye"></i> Ver
                            </button>
                            <button onclick="excluirRegistro(${h.id})" class="px-2 py-1.5 rounded-lg bg-zinc-800 hover:bg-red-600 text-zinc-400 hover:text-white transition-colors border border-zinc-700">
                                <i class="fa-solid fa-trash"></i>
                            </button>
                        </div>
                    </div>
                `;
            });
        }

        document.getElementById('pag_info_inicio').innerText = data.total === 0 ? 0 : ((histPaginaAtual - 1) * histLimite) + 1;
        document.getElementById('pag_info_fim').innerText = Math.min(histPaginaAtual * histLimite, data.total);
        document.getElementById('pag_info_total').innerText = data.total;

        document.getElementById('btn_pag_ant').disabled = histPaginaAtual === 1;
        document.getElementById('btn_pag_prox').disabled = histPaginaAtual >= data.total_paginas || data.total === 0;

    } catch (error) {
        tabela.innerHTML = `<div class="p-10 text-center"><p class="text-red-400 font-bold"><i class="fa-solid fa-triangle-exclamation"></i> Erro: ${error.message}</p></div>`;
    }
}

// ==========================================
// MÓDULO: VIDEO FORGE (ATUALIZADO)
// ==========================================
let formatoVideoForgeAtual = "vertical";
let midiaTypeForgeAtual = "imagem";

function setFormatoVideoForge(formato) {
    formatoVideoForgeAtual = formato;
    const btnV = document.getElementById('btn_vf_vertical');
    const btnH = document.getElementById('btn_vf_horizontal');

    if(formato === 'vertical') {
        btnV.className = "flex-1 py-2.5 text-[10px] font-bold rounded-lg bg-indigo-600 text-white shadow-md transition-all flex flex-col items-center gap-1 border border-indigo-500";
        btnH.className = "flex-1 py-2.5 text-[10px] font-bold rounded-lg text-zinc-500 hover:text-white transition-all flex flex-col items-center gap-1";
    } else {
        btnH.className = "flex-1 py-2.5 text-[10px] font-bold rounded-lg bg-indigo-600 text-white shadow-md transition-all flex flex-col items-center gap-1 border border-indigo-500";
        btnV.className = "flex-1 py-2.5 text-[10px] font-bold rounded-lg text-zinc-500 hover:text-white transition-all flex flex-col items-center gap-1";
    }
}

function setMidiaTypeForge(tipo) {
    midiaTypeForgeAtual = tipo;
    const btnImg = document.getElementById('btn_type_img');
    const btnVid = document.getElementById('btn_type_vid');
    const labelMidia = document.getElementById('label_midia_principal');
    const inputMidia = document.getElementById('upload_midias');

    if(tipo === 'imagem') {
        btnImg.className = "flex-1 py-2 text-[10px] font-bold rounded-lg bg-zinc-800 text-white border border-zinc-700/50 shadow-sm transition-all flex items-center justify-center gap-2";
        btnVid.className = "flex-1 py-2 text-[10px] font-bold rounded-lg text-zinc-500 hover:text-white transition-all flex items-center justify-center gap-2";
        labelMidia.innerHTML = '<i class="fa-solid fa-images text-cyan-400 mr-1"></i> Selecione as Imagens';
        inputMidia.accept = "image/jpeg,image/png,image/webp";
    } else {
        btnVid.className = "flex-1 py-2 text-[10px] font-bold rounded-lg bg-zinc-800 text-white border border-zinc-700/50 shadow-sm transition-all flex items-center justify-center gap-2";
        btnImg.className = "flex-1 py-2 text-[10px] font-bold rounded-lg text-zinc-500 hover:text-white transition-all flex items-center justify-center gap-2";
        labelMidia.innerHTML = '<i class="fa-solid fa-video text-purple-400 mr-1"></i> Selecione os Clipes de Vídeo';
        inputMidia.accept = "video/mp4,video/x-m4v,video/*";
    }
}

async function renderizarVideo() {
    const inputVoz = document.getElementById('upload_voz');
    const inputSrt = document.getElementById('upload_srt');
    const inputBgm = document.getElementById('upload_bgm');
    const inputMidias = document.getElementById('upload_midias');
    const btn = document.getElementById('btn_render');
    const txtBtn = document.getElementById('txt_btn_render');
    const statusDiv = document.getElementById('status_render');
    const resultDiv = document.getElementById('resultado_video');

    if (!inputVoz.files[0] || !inputSrt.files[0] || inputMidias.files.length === 0) {
        return alert("Voz, Legenda e os arquivos de Mídia são obrigatórios!");
    }

    const formData = new FormData();
    formData.append("voz", inputVoz.files[0]);
    formData.append("legenda", inputSrt.files[0]);
    formData.append("formato_video", formatoVideoForgeAtual);
    formData.append("midia_type", midiaTypeForgeAtual);
    
    if (inputBgm && inputBgm.files[0]) formData.append("bgm", inputBgm.files[0]);
    
    for (let i = 0; i < inputMidias.files.length; i++) {
        formData.append("imagens", inputMidias.files[i]);
    }

    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    txtBtn.innerHTML = `Aquecendo a Forja... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;
    
    resultDiv.classList.add('hidden');
    resultDiv.classList.remove('flex');
    statusDiv.classList.remove('hidden');
    statusDiv.innerHTML = `
        <div class="w-20 h-20 mx-auto rounded-2xl bg-[#09090b] border border-indigo-500/50 flex items-center justify-center mb-6 shadow-[0_0_20px_rgba(99,102,241,0.3)] relative">
            <i class="fa-solid fa-fire-burner text-4xl text-indigo-500 fa-beat"></i>
        </div>
        <h3 class="text-base font-black text-indigo-400 tracking-tight animate-pulse italic">FUNDINDO MATERIAIS...</h3>
        <p class="text-xs text-zinc-500 mt-2">A nossa IA está processando e fundindo todos os materiais no backend. Aguarde alguns minutos e não feche esta tela.</p>
    `;

    try {
        const response = await fetch("/api/v1/video-forge", {
            method: 'POST',
            body: formData
        });

        const dados = await response.json();
        
        if (!response.ok) throw new Error(dados.detail || "Erro ao forjar vídeo.");

        statusDiv.classList.add('hidden');
        resultDiv.classList.remove('hidden');
        resultDiv.classList.add('flex');
        
        document.getElementById('player_final').src = dados.video_url;
        document.getElementById('btn_baixar_mp4').href = dados.video_url;

        if (dados.novo_saldo !== undefined) {
            const paineisDeCoins = document.querySelectorAll('.fa-coins');
            paineisDeCoins.forEach(icone => {
                const elementoPai = icone.closest('p'); 
                if (elementoPai) {
                    elementoPai.innerHTML = `<i class="fa-solid fa-coins"></i> ${dados.novo_saldo.toLocaleString('pt-BR')} coins`;
                    elementoPai.classList.add('text-indigo-400', 'scale-110');
                    setTimeout(() => elementoPai.classList.remove('text-indigo-400', 'scale-110'), 500);
                }
            });
        }

    } catch (error) {
        statusDiv.innerHTML = `
            <div class="w-20 h-20 mx-auto rounded-2xl bg-red-500/10 border border-red-500/30 flex items-center justify-center mb-6">
                <i class="fa-solid fa-triangle-exclamation text-4xl text-red-500"></i>
            </div>
            <h3 class="text-base font-black text-red-400 tracking-tight">FALHA NA FORJA</h3>
            <p class="text-xs text-zinc-500 mt-2">${error.message}</p>
        `;
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        txtBtn.innerHTML = `FORJAR VÍDEO MP4`;
    }
}
