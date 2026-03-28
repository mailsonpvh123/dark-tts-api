// ==========================================
// CONFIGURAÇÕES GLOBAIS
// ==========================================
const URL_API_VOZES = "/api/v1/vozes"; 
const URL_API_DIRETA = "/api/v1/gerar_narracao"; 
let vozesData = [];
let vozSelecionada = "padrao-pt-BR-AntonioNeural"; 
let srtGlobal = ""; 
let timerDebounceCusto = null; 
let abaVozAtiva = "padrao";

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
            if (path === '/audio-mixer') icon.classList.add('text-amber-400');
            if (path === '/meta-seo') icon.classList.add('text-blue-400');
            if (path === '/thumb-maker') icon.classList.add('text-pink-400');
        }
    });

    const textoVoice = localStorage.getItem('texto_pendente_voice');
    if (textoVoice && document.getElementById('texto_voz')) {
        document.getElementById('texto_voz').value = textoVoice;
        localStorage.removeItem('texto_pendente_voice');
        if(typeof recalcularCustoVoz === 'function') recalcularCustoVoz();
    }

    if(document.getElementById('lista_vozes')) {
        try {
            const resposta = await fetch("/vozes");
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

function despacharParaVoice(idCampoOrigem) {
    const texto = document.getElementById(idCampoOrigem).value;
    if(!texto || texto.trim() === "") return alert("Aviso: O texto está vazio!"); 
    localStorage.setItem('texto_pendente_voice', texto);
    window.location.href = '/voice-synthesizer'; 
}

// ==========================================
// FUNÇÕES DE INTERFACE (AS 3 ABAS)
// ==========================================
function alternarAbaVozes(tipo) {
    abaVozAtiva = tipo;
    
    const btnPadrao = document.getElementById('aba_btn_padrao');
    const btnCreator = document.getElementById('aba_btn_creator');
    const btnCinematic = document.getElementById('aba_btn_cinematic');
    
    // Reseta visuais
    [btnPadrao, btnCreator, btnCinematic].forEach(btn => {
        if(btn) btn.className = "flex-1 py-2 text-xs font-bold rounded-md text-zinc-500 hover:text-white transition-all";
    });
    
    if (tipo === 'padrao') {
        if(btnPadrao) btnPadrao.className = "flex-1 py-2 text-xs font-bold rounded-md bg-zinc-800 text-white shadow-sm transition-all";
        atualizarInfoTier(
            "Qualidade Standard", 
            "Vozes sintéticas de alta eficiência. Ideais para testes, rascunhos ou canais de curiosidades com alto volume de postagem.",
            "text-purple-400", "border-purple-500/20"
        );
    } else if (tipo === 'creator') {
        if(btnCreator) btnCreator.className = "flex-1 py-2 text-xs font-bold rounded-md bg-zinc-800 text-blue-400 shadow-sm transition-all";
        atualizarInfoTier(
            "Qualidade Creator", 
            "Vozes neurais avançadas com capacidade de atuação. A escolha definitiva para quem já monetiza e busca retenção com ótimo custo-benefício.",
            "text-blue-400", "border-blue-500/20"
        );
    } else if (tipo === 'cinematic') {
        if(btnCinematic) btnCinematic.className = "flex-1 py-2 text-xs font-bold rounded-md bg-zinc-800 text-amber-400 shadow-sm transition-all";
        atualizarInfoTier(
            "Qualidade Cinematic (Ultra-Realista)", 
            "Atuação de estúdio e realismo absoluto. Vozes que respiram e se adaptam naturalmente ao texto. Recomendado para documentários de elite e canais Dark premium.",
            "text-amber-500", "border-amber-500/30"
        );
    }
    
    const primeiraDaLista = vozesData.find(v => v.tipo === tipo);
    if(primeiraDaLista) selecionarVoz(primeiraDaLista.shortName);
    
    renderizarListaVozes();
}

function atualizarInfoTier(titulo, desc, corTexto, corBorda) {
    const infoContainer = document.getElementById('info_tier');
    if(!infoContainer) return;
    
    infoContainer.innerHTML = `
        <div class="bg-[#09090b] p-4 rounded-xl border ${corBorda} shadow-inner">
            <h4 class="text-sm font-bold ${corTexto} mb-1"><i class="fa-solid fa-circle-info mr-1"></i> ${titulo}</h4>
            <p class="text-xs text-zinc-400 leading-relaxed">${desc}</p>
        </div>
    `;
}

function renderizarListaVozes() {
    const container = document.getElementById('lista_vozes');
    if(!container) return;
    container.innerHTML = '';
    
    const vozesFiltradas = vozesData.filter(v => v.tipo === abaVozAtiva);
    
    vozesFiltradas.forEach(v => {
        let isSelected = v.shortName === vozSelecionada;
        let isCinematic = v.tipo === 'cinematic';
        let isCreator = v.tipo === 'creator';

        let baseClass = isCinematic ? "bg-amber-500/5 hover:border-amber-500/40" : (isCreator ? "bg-blue-500/5 hover:border-blue-500/40" : "bg-[#09090b] hover:border-purple-500/40");
        let cardClass = isSelected 
            ? "border-emerald-500 bg-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.15)]" 
            : `border-zinc-800 ${baseClass}`;
            
        let iconClass = isCinematic ? 'fa-star text-amber-400' : (isCreator ? 'fa-clapperboard text-blue-400' : (v.gender === 'Female' ? 'fa-face-smile-beam text-pink-400' : 'fa-user-astronaut text-purple-400'));
        
        let tagsHtml = "";
        if (isCinematic) tagsHtml = '<span class="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">Cinematic</span>';
        else if (isCreator) tagsHtml = '<span class="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">Creator</span>';
        else tagsHtml = (v.gender === 'Female' ? '<span class="text-[10px] font-bold text-pink-400 bg-pink-500/10 px-2 py-0.5 rounded border border-pink-500/20">Feminino</span>' : '<span class="text-[10px] font-bold text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">Masculino</span>');

        let nomeDisplay = v.name;
        if (!isCinematic && !isCreator) {
            // Limpa nomes muito grandes do Standard
            nomeDisplay = v.shortName.replace(/padrao-|Neural|Multilingual|V2/ig, '').trim(); 
            let partes = nomeDisplay.split('-');
            if(partes.length >= 3) {
                nomeDisplay = `${partes.slice(2).join(' ')} - ${partes[0].toUpperCase()}`;
            }
        }

        container.innerHTML += `
            <div class="flex items-center justify-between p-4 rounded-xl border ${cardClass} cursor-pointer transition-all duration-300 group relative z-10" onclick="selecionarVoz('${v.shortName}')">
                <div class="flex items-center gap-4">
                    <div class="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-700/50 flex items-center justify-center group-hover:scale-110 transition-transform shadow-inner shrink-0">
                        <i class="fa-solid ${iconClass} text-lg drop-shadow-md"></i>
                    </div>
                    <div>
                        <p class="text-[13px] font-bold text-white group-hover:text-emerald-300 transition-colors leading-tight mb-1">${nomeDisplay}</p>
                        <div class="flex items-center gap-2">
                            ${tagsHtml}
                        </div>
                    </div>
                </div>
                <button class="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700/50 flex items-center justify-center text-zinc-400 hover:bg-emerald-500 hover:text-white hover:border-emerald-400 transition-all shadow-md shrink-0" onclick="tocarPreview(event, '${v.shortName}')">
                    <i id="play_icon_${v.shortName}" class="fa-solid fa-play text-xs ml-0.5"></i>
                </button>
            </div>`;
    });
}

function selecionarVoz(sn) { 
    vozSelecionada = sn; 
    
    const painelStandard = document.getElementById('controles_standard');
    const painelCreator = document.getElementById('controles_creator');
    
    if(sn.includes("cinematic-")) {
        if(painelStandard) painelStandard.classList.add('hidden');
        if(painelCreator) painelCreator.classList.add('hidden'); // Cinematic atua sozinho pelo roteiro
    } else if (sn.includes("creator-")) {
        if(painelStandard) painelStandard.classList.add('hidden');
        if(painelCreator) painelCreator.classList.remove('hidden');
    } else {
        if(painelCreator) painelCreator.classList.add('hidden');
        if(painelStandard) painelStandard.classList.remove('hidden');
    }
    
    renderizarListaVozes(); 
    recalcularCustoVoz(); 
}

function recalcularCustoVoz() {
    clearTimeout(timerDebounceCusto);
    timerDebounceCusto = setTimeout(() => {
        const inputTexto = document.getElementById('texto_voz');
        if(!inputTexto) return;
        
        const texto = inputTexto.value;
        const tamanho = texto.length;
        const btnTxt = document.getElementById('txt_btn_voz');
        const contador = document.getElementById('contador_caracteres_voz');
        
        const isCinematic = vozSelecionada.includes("cinematic-");
        const isCreator = vozSelecionada.includes("creator-");
        
        if(contador) contador.innerText = `${tamanho} caracteres`;

        if(btnTxt) {
            if(isCinematic) {
                let custo = Math.max(1, Math.ceil((tamanho / 900.0) * 50));
                btnTxt.innerHTML = `Sintetizar Cinematic (<span class="text-amber-900 drop-shadow-md">${custo} Coins</span>)`;
                document.getElementById('btn_gerar_voz').className = "w-full mt-6 bg-amber-500 hover:bg-amber-400 text-amber-950 font-black py-4 px-4 rounded-xl shadow-[0_0_20px_rgba(245,158,11,0.3)] transition-all flex items-center justify-center gap-2 group border border-amber-400 relative z-10";
            } else if (isCreator) {
                let custo = Math.max(1, Math.ceil((tamanho / 900.0) * 12));
                btnTxt.innerHTML = `Sintetizar Creator (<span class="text-blue-900 drop-shadow-md">${custo} Coins</span>)`;
                document.getElementById('btn_gerar_voz').className = "w-full mt-6 bg-blue-500 hover:bg-blue-400 text-blue-950 font-black py-4 px-4 rounded-xl shadow-[0_0_20px_rgba(59,130,246,0.3)] transition-all flex items-center justify-center gap-2 group border border-blue-400 relative z-10";
            } else {
                btnTxt.innerHTML = `Sintetizar Standard (30 Coins)`;
                document.getElementById('btn_gerar_voz').className = "w-full mt-6 bg-purple-600 hover:bg-purple-500 text-white font-bold py-4 px-4 rounded-xl shadow-[0_0_20px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center gap-2 group border border-purple-500/50 relative z-10";
            }
        }
    }, 300); 
}

// ==========================================
// CONTROLES DE SLIDERS (Edge)
// ==========================================
function ajustarVelocidade(delta) {
    const slider = document.getElementById('velocidade');
    let newVal = parseFloat(slider.value) + delta;
    if(newVal > 2.0) newVal = 2.0;
    if(newVal < 0.5) newVal = 0.5;
    slider.value = newVal.toFixed(1);
    document.getElementById('val_v').innerText = slider.value + 'x';
}

function ajustarPitch(delta) {
    const slider = document.getElementById('pitch');
    let newVal = parseInt(slider.value) + delta;
    if(newVal > 50) newVal = 50;
    if(newVal < -50) newVal = -50;
    slider.value = newVal;
    document.getElementById('val_p').innerText = slider.value + 'Hz';
}

// ==========================================
// INTEGRAÇÃO COM A API (GERAÇÃO DE VOZ)
// ==========================================
async function tocarPreview(event, shortName) {
    event.stopPropagation();
    const playerPreview = document.getElementById('player_preview') || new Audio();
    playerPreview.pause();

    const icon = document.getElementById(`play_icon_${shortName}`);
    icon.className = "fa-solid fa-circle-notch fa-spin text-white";
    
    try {
        const res = await fetch("/gerar_narracao", { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ 
                texto: "Olá, sou uma voz neural da sua plataforma. Esta é a minha qualidade de narração.", 
                voz: shortName, 
                velocidade: 1.0, 
                pitch: 0 
            }) 
        });
        
        const dados = await res.json();
        if(dados.status === "erro") throw new Error(dados.mensagem);

        playerPreview.src = "data:audio/mp3;base64," + dados.audio_base64;
        playerPreview.play();
        
        playerPreview.onended = () => { icon.className = "fa-solid fa-play text-xs ml-0.5"; };
    } catch(e) {
        alert("Erro no Preview: " + e.message);
        icon.className = "fa-solid fa-play text-xs ml-0.5"; 
    } 
}

async function gerarAudioCompleto() {
    const btn = document.getElementById('btn_gerar_voz');
    const txtBtn = document.getElementById('txt_btn_voz');
    const texto = document.getElementById('texto_voz').value;
    const playerContainer = document.getElementById('player_container');
    
    const instrucaoElement = document.getElementById('instrucao_estilo');
    const instrucaoEstilo = instrucaoElement ? instrucaoElement.value : "";
    
    if(!texto.trim()) return alert("Digite um texto antes de sintetizar!");

    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    
    const isCinematic = vozSelecionada.includes("cinematic-");
    const isCreator = vozSelecionada.includes("creator-");

    txtBtn.innerHTML = `Processando no Estúdio... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;
    playerContainer.classList.remove('hidden');
    
    let icone = isCinematic ? "fa-star text-amber-400" : (isCreator ? "fa-clapperboard text-blue-400" : "fa-microphone-lines text-purple-400");
    let msgExtra = texto.length > 4000 ? "<br><span class='text-[10px] text-zinc-500'>O roteiro longo está sendo renderizado por partes para garantir a qualidade. Aguarde.</span>" : "";
    
    playerContainer.innerHTML = `<p class="animate-pulse text-center font-bold text-sm"><i class="fa-solid ${icone} fa-fade mr-2"></i> Renderizando o seu áudio...${msgExtra}</p>`;

    const payload = { 
        texto: texto, 
        voz: vozSelecionada, 
        velocidade: parseFloat(document.getElementById('velocidade').value), 
        pitch: parseInt(document.getElementById('pitch').value),
        instrucao_estilo: instrucaoEstilo
    };

    try {
        const res = await fetch("/gerar_narracao", { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(payload) 
        });
        
        if(!res.ok) {
            let erroReal = "Erro no servidor.";
            try { const dadosErro = await res.json(); erroReal = dadosErro.detail || erroReal; } catch(e) {}
            throw new Error(erroReal);
        }
        
        const dados = await res.json();

        if(dados.novo_saldo !== undefined) {
            const paineisDeCoins = document.querySelectorAll('.fa-coins');
            paineisDeCoins.forEach(icone => {
                const elementoPai = icone.closest('p'); 
                if(elementoPai) {
                    elementoPai.innerHTML = `<i class="fa-solid fa-coins"></i> ${dados.novo_saldo.toLocaleString('pt-BR')} coins`;
                    elementoPai.classList.add('text-emerald-400', 'scale-110');
                    setTimeout(() => elementoPai.classList.remove('text-emerald-400', 'scale-110'), 500);
                }
            });
        }

        playerContainer.innerHTML = `
            <div class="flex items-center gap-2 mb-3">
                <i class="fa-solid fa-circle-check text-emerald-400 drop-shadow-[0_0_5px_rgba(16,185,129,0.8)]"></i>
                <p class="text-xs text-emerald-400 font-bold uppercase tracking-wider">Locução Finalizada</p>
            </div>
            <audio controls class="w-full h-12 bg-zinc-900 rounded-lg outline-none shadow-inner">
                <source src="data:audio/mp3;base64,${dados.audio_base64}" type="audio/mp3">
            </audio>
        `;
    } catch (e) {
        const isCoinError = e.message.includes('Coins insuficientes');
        const erroClass = isCoinError ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20';
        playerContainer.innerHTML = `<div class="${erroClass} border p-4 rounded-lg text-center font-bold text-sm"><i class="fa-solid fa-triangle-exclamation mb-2 text-2xl block"></i> ${e.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        recalcularCustoVoz();
    }
}

function contarPalavrasLocal(texto) {
    if (!texto || texto.trim() === "") return 0;
    return texto.trim().split(/\s+/).length;
}
