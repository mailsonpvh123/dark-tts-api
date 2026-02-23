// ==========================================
// CONFIGURAÇÕES GLOBAIS
// ==========================================
const URL_API_VOZES = "https://tts.zappclube.com.br/vozes"; 
const URL_API_DIRETA = "https://tts.zappclube.com.br/gerar_narracao"; 
let vozesData = [];
let vozSelecionada = "pt-BR-AntonioNeural"; 
let srtGlobal = ""; 

// ==========================================
// INICIALIZAÇÃO E DESTAQUE DO MENU
// ==========================================
window.onload = async function() {
    // 1. Destaque Automático do Menu Lateral com base na URL
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

    // 2. Receptor de Dados (Texto vindo de outra página)
    const textoVoice = localStorage.getItem('texto_pendente_voice');
    if (textoVoice && document.getElementById('texto_voz')) {
        document.getElementById('texto_voz').value = textoVoice;
        localStorage.removeItem('texto_pendente_voice');
    }

    // 3. Carregamento de Vozes
    if(document.getElementById('lista_vozes')) {
        try {
            const resposta = await fetch(URL_API_VOZES);
            const dados = await resposta.json();
            vozesData = dados.vozes || dados;
            renderizarListaVozes();
        } catch (error) { 
            console.log("Erro TTS:", error); 
        }
    }
};

// ==========================================
// NAVEGAÇÃO ENTRE FERRAMENTAS
// ==========================================
function despacharParaVoice(idCampoOrigem) {
    const texto = document.getElementById(idCampoOrigem).value;
    if(!texto || texto.trim() === "") return alert("Aviso: O texto está vazio!"); 

    localStorage.setItem('texto_pendente_voice', texto);
    window.location.href = '/voice-synthesizer'; 
}

function enviarScriptParaVoice() { despacharParaVoice('script_final_editavel'); }
function enviarParaphraserParaVoice() { despacharParaVoice('paraphraser_resultado'); }

// ==========================================
// FUNÇÕES DO VOICE SYNTHESIZER
// ==========================================
function renderizarListaVozes() {
    const container = document.getElementById('lista_vozes');
    if(!container) return;
    container.innerHTML = '';
    vozesData.forEach(v => {
        let cardClass = v.shortName === vozSelecionada ? "border-emerald-500 bg-emerald-500/5" : "border-zinc-800 bg-[#09090b]";
        container.innerHTML += `
            <div class="flex items-center justify-between p-3 rounded-xl border ${cardClass} cursor-pointer transition-all" onclick="selecionarVoz('${v.shortName}')">
                <div class="flex items-center gap-3">
                    <div class="w-10 h-10 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400"><i class="fa-solid fa-robot"></i></div>
                    <div><p class="text-sm font-bold text-white">${v.shortName}</p></div>
                </div>
                <button class="w-8 h-8 rounded-full bg-zinc-800 text-zinc-400" onclick="tocarPreview(event, '${v.shortName}')">
                    <i id="play_icon_${v.shortName}" class="fa-solid fa-play text-xs"></i>
                </button>
            </div>`;
    });
}

function selecionarVoz(sn) { vozSelecionada = sn; renderizarListaVozes(); }

async function tocarPreview(event, shortName) {
    event.stopPropagation();
    const icon = document.getElementById(`play_icon_${shortName}`);
    icon.className = "fa-solid fa-circle-notch fa-spin";
    try {
        const res = await fetch(URL_API_DIRETA, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto: "Olá, sou uma voz neural.", voz: shortName, velocidade: 1.0, pitch: 0, volume: 0 }) });
        const dados = await res.json();
        document.getElementById('player_preview').src = "data:audio/mp3;base64," + dados.audio_base64;
        document.getElementById('player_preview').play();
    } finally { icon.className = "fa-solid fa-play"; }
}

async function gerarAudioCompleto() {
    const btn = document.getElementById('btn_gerar_voz');
    const texto = document.getElementById('texto_voz').value;
    const playerContainer = document.getElementById('player_container');
    
    if(!texto.trim()) return alert("Digite um texto!");

    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i> Processando...`;
    playerContainer.classList.remove('hidden');
    playerContainer.innerHTML = `<p class="text-purple-400 animate-pulse text-center">A IA está gravando...</p>`;

    const payload = { 
        texto: texto, 
        voz: vozSelecionada, 
        velocidade: parseFloat(document.getElementById('velocidade').value), 
        pitch: parseInt(document.getElementById('pitch').value), 
        volume: 0 
    };

    try {
        const res = await fetch(URL_API_DIRETA, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const dados = await res.json();
        
        if(dados.status === "erro") throw new Error(dados.mensagem);

        playerContainer.innerHTML = `
            <audio controls class="w-full h-12 bg-zinc-900 rounded-lg">
                <source src="data:audio/mp3;base64,${dados.audio_base64}" type="audio/mp3">
            </audio>
        `;
    } catch (e) {
        playerContainer.innerHTML = `<p class="text-red-400">Erro: ${e.message}</p>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Sintetizar Voz`;
    }
}

function ajustarVelocidade(delta) {
    const slider = document.getElementById('velocidade');
    slider.value = (parseFloat(slider.value) + delta).toFixed(1);
    document.getElementById('val_v').innerText = slider.value + 'x';
}

function ajustarPitch(delta) {
    const slider = document.getElementById('pitch');
    slider.value = parseInt(slider.value) + delta;
    document.getElementById('val_p').innerText = slider.value + 'Hz';
}
