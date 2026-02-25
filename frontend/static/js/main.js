// ==========================================
// CONFIGURAÇÕES GLOBAIS
// ==========================================
const URL_API_VOZES = "/vozes"; 
const URL_API_DIRETA = "/gerar_narracao"; 
let vozesData = [];
let vozSelecionada = "pt-BR-AntonioNeural"; 
let srtGlobal = ""; 

// O uso do DOMContentLoaded garante que o JS cole as informações no exato momento, sem falhas
document.addEventListener('DOMContentLoaded', async function() {
    
    // 1. Destaque Automático do Menu Lateral
    const path = window.location.pathname;
    document.querySelectorAll('.menu-btn').forEach(link => {
        if (link.getAttribute('href') === path) {
            link.classList.add('text-white', 'bg-zinc-800/80', 'border-zinc-700');
            link.classList.remove('text-zinc-400');
            const icon = link.querySelector('i');
            if (path === '/gen-insights') icon.classList.add('text-yellow-400');
            if (path === '/paraphraser') icon.classList.add('text-pink-400');
            if (path === '/script-forge') icon.classList.add('text-orange-400');
            if (path === '/voice-synthesizer') icon.classList.add('text-purple-400');
            if (path === '/gen-legends') icon.classList.add('text-cyan-400');
        }
    });

    // 2. RECEPTORES DAS ESTEIRAS DE PRODUÇÃO (Aqui que o texto é colado automaticamente!)
    const textoVoice = localStorage.getItem('texto_pendente_voice');
    if (textoVoice && document.getElementById('texto_voz')) {
        document.getElementById('texto_voz').value = textoVoice;
        localStorage.removeItem('texto_pendente_voice');
    }

    const textoScript = localStorage.getItem('ideia_pendente_script');
    if (textoScript && document.getElementById('script_ideia_base')) {
        document.getElementById('script_ideia_base').value = textoScript;
        localStorage.removeItem('ideia_pendente_script');
        if(typeof contarPalavrasLocal === 'function') contarPalavrasLocal('script_ideia_base', 'contador_script_in');
    }

    const textoPara = localStorage.getItem('texto_pendente_paraphraser');
    if (textoPara && document.getElementById('paraphraser_conteudo')) {
        document.getElementById('paraphraser_conteudo').value = textoPara;
        localStorage.removeItem('texto_pendente_paraphraser');
        if(typeof contarPalavrasLocal === 'function') contarPalavrasLocal('paraphraser_conteudo', 'contador_palavras_in');
    }

    // 3. Carregamento de Vozes (Com caminhos relativos)
    if(document.getElementById('lista_vozes')) {
        try {
            const resposta = await fetch(URL_API_VOZES);
            if (!resposta.ok) throw new Error("Falha ao comunicar com a API.");
            const dados = await resposta.json();
            
            if(dados.status === "erro") throw new Error(dados.mensagem);
            
            vozesData = dados.vozes || dados;
            renderizarListaVozes();
        } catch (error) { 
            console.log("Erro TTS:", error);
            document.getElementById('lista_vozes').innerHTML = `
                <div class="text-center text-red-500 py-10">
                    <i class="fa-solid fa-triangle-exclamation text-3xl mb-3 drop-shadow-[0_0_10px_rgba(239,68,68,0.5)]"></i>
                    <br><span class="text-sm font-bold">Erro de Conexão</span>
                    <p class="text-xs text-zinc-500 mt-1">Não foi possível carregar as vozes.</p>
                </div>`;
        }
    }
});

// ==========================================
// FUNÇÕES DE DISPARO PARA A ESTEIRA
// ==========================================
function despacharParaVoice(idCampoOrigem) {
    const texto = document.getElementById(idCampoOrigem).value;
    if(!texto || texto.trim() === "") return alert("Aviso: O texto está vazio!"); 
    localStorage.setItem('texto_pendente_voice', texto);
    window.location.href = '/voice-synthesizer'; 
}

function despacharParaParaphraser(idCampoOrigem) {
    const texto = document.getElementById(idCampoOrigem).value;
    if(!texto || texto.trim() === "") return alert("Aviso: O texto está vazio!"); 
    localStorage.setItem('texto_pendente_paraphraser', texto);
    window.location.href = '/paraphraser'; 
}

function enviarScriptParaVoice() { despacharParaVoice('script_final_editavel'); }
function enviarParaphraserParaVoice() { despacharParaVoice('paraphraser_resultado'); }
function enviarLegendsParaParaphraser() { despacharParaParaphraser('legends_txt_resultado'); }

function contarPalavrasLocal(textAreaId, contadorId) {
    const el = document.getElementById(textAreaId);
    const contador = document.getElementById(contadorId);
    if(el && contador) {
        const texto = el.value.trim();
        const palavras = texto === "" ? 0 : texto.split(/\s+/).length;
        contador.innerText = `${palavras} palavras`;
    }
}

// ==========================================
// FUNÇÕES DO VOICE SYNTHESIZER
// ==========================================
function renderizarListaVozes() {
    const container = document.getElementById('lista_vozes');
    if(!container) return;
    
    container.innerHTML = '';
    vozesData.forEach(v => {
        let cardClass = v.shortName === vozSelecionada ? "border-emerald-500 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.15)]" : "border-zinc-800 bg-[#09090b] hover:border-purple-500/50 hover:bg-purple-500/5";
        
        container.innerHTML += `
            <div class="flex items-center justify-between p-3 rounded-xl border ${cardClass} cursor-pointer transition-all group relative z-10" onclick="selecionarVoz('${v.shortName}')">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 group-hover:scale-110 transition-transform"><i class="fa-solid fa-robot"></i></div>
                    <div><p class="text-sm font-bold text-white group-hover:text-purple-300 transition-colors">${v.shortName}</p></div>
                </div>
                <button class="w-9 h-9 rounded-full bg-zinc-800 border border-zinc-700/50 flex items-center justify-center text-zinc-400 hover:bg-emerald-500 hover:text-white transition-all" onclick="tocarPreview(event, '${v.shortName}')">
                    <i id="play_icon_${v.shortName}" class="fa-solid fa-play text-xs ml-0.5"></i>
                </button>
            </div>`;
    });
}

function selecionarVoz(sn) { 
    vozSelecionada = sn; 
    renderizarListaVozes(); 
}

async function tocarPreview(event, shortName) {
    event.stopPropagation();
    
    const playerPreview = document.getElementById('player_preview') || new Audio();
    playerPreview.pause();

    const icon = document.getElementById(`play_icon_${shortName}`);
    icon.className = "fa-solid fa-circle-notch fa-spin text-white";
    
    try {
        const res = await fetch(URL_API_DIRETA, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ texto: "Olá, sou uma voz neural da sua plataforma.", voz: shortName, velocidade: 1.0, pitch: 0, volume: 0 }) 
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
    const texto = document.getElementById('texto_voz').value;
    const playerContainer = document.getElementById('player_container');
    
    if(!texto.trim()) return alert("Digite um texto antes de sintetizar!");

    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-emerald-400"></i> <span>Gravando na Nuvem...</span>`;
    
    playerContainer.classList.remove('hidden');
    playerContainer.innerHTML = `<p class="text-emerald-400 animate-pulse text-center font-bold text-sm">O estúdio neural está gravando a sua locução...</p>`;

    const payload = { 
        texto: texto, 
        voz: vozSelecionada, 
        velocidade: parseFloat(document.getElementById('velocidade').value), 
        pitch: parseInt(document.getElementById('pitch').value), 
        volume: 0 
    };

    try {
        const res = await fetch(URL_API_DIRETA, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify(payload) 
        });
        
        const dados = await res.json();
        if(dados.status === "erro") throw new Error(dados.mensagem);

        playerContainer.innerHTML = `
            <div class="flex items-center gap-2 mb-3">
                <i class="fa-solid fa-circle-check text-emerald-400 drop-shadow-[0_0_5px_rgba(16,185,129,0.8)]"></i>
                <p class="text-xs text-emerald-400 font-bold uppercase tracking-wider">Áudio Finalizado</p>
            </div>
            <audio controls class="w-full h-12 bg-zinc-900 rounded-lg outline-none shadow-inner">
                <source src="data:audio/mp3;base64,${dados.audio_base64}" type="audio/mp3">
            </audio>
        `;
    } catch (e) {
        playerContainer.innerHTML = `<p class="text-red-400 text-sm font-bold"><i class="fa-solid fa-triangle-exclamation"></i> Erro: ${e.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> <span>Sintetizar Voz (380 coins)</span>`;
    }
}

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
