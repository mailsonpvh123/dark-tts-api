// ==========================================
// CONFIGURAÇÕES GLOBAIS E ESTEIRA
// ==========================================
const URL_API_VOZES = "/vozes"; 
const URL_API_DIRETA = "/gerar_narracao"; 
let vozesData = [];
let vozSelecionada = "pt-BR-AntonioNeural"; 
let srtGlobal = ""; 

document.addEventListener('DOMContentLoaded', async function() {
    const path = window.location.pathname;
    
    // Pinta o botão correto no menu lateral
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

    // RECEPTORES DA ESTEIRA (Ouvidos Mágicos)
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

    // CARREGADOR DE VOZES (Só roda na aba do Voice Synth)
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

// FUNÇÕES DE DESPACHO PARA A ESTEIRA (Rodam de qualquer página)
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
// FUNÇÕES DO VOICE SYNTHESIZER (UI PREMIUM ABSOLUTA)
// ==========================================
function renderizarListaVozes() {
    const container = document.getElementById('lista_vozes');
    if(!container) return;
    
    container.innerHTML = '';
    
    vozesData.forEach(v => {
        let isSelected = v.shortName === vozSelecionada;
        let cardClass = isSelected 
            ? "border-emerald-500 bg-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.15)]" 
            : "border-zinc-800 bg-[#09090b] hover:border-purple-500/40 hover:bg-purple-500/5";
            
        let iconClass = v.gender === 'Female' ? 'fa-face-smile-beam text-pink-400' : 'fa-user-astronaut text-blue-400';
        let genderTag = v.gender === 'Female' 
            ? '<span class="text-[10px] font-bold text-pink-400 bg-pink-500/10 px-2 py-0.5 rounded border border-pink-500/20">Feminino</span>'
            : '<span class="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">Masculino</span>';

        let partes = v.shortName.split('-');
        let nomeDisplay = v.shortName.replace(/Neural/ig, '').replace(/Multilingual/ig, '').replace(/V2/ig, '').trim(); 
        
        if (partes.length >= 3) {
            let idiomaCodigo = partes[0].toLowerCase();
            let regiaoCodigo = partes[1].toUpperCase();
            
            let nomeAtor = partes.slice(2).join(' ');
            nomeAtor = nomeAtor.replace(/Neural/ig, '').replace(/Multilingual/ig, '').replace(/V2/ig, '').trim();
            
            let mapaIdiomas = {
                'pt': 'Português', 'en': 'Inglês', 'es': 'Espanhol', 'fr': 'Francês',
                'it': 'Italiano', 'de': 'Alemão', 'ja': 'Japonês', 'ko': 'Coreano',
                'zh': 'Chinês', 'ru': 'Russo', 'nl': 'Holandês', 'tr': 'Turco', 'pl': 'Polonês'
            };
            
            let idiomaDisplay = mapaIdiomas[idiomaCodigo] || idiomaCodigo.toUpperCase();
            nomeDisplay = `${nomeAtor} - ${idiomaDisplay} - ${regiaoCodigo}`;
        }

        container.innerHTML += `
            <div class="flex items-center justify-between p-4 rounded-xl border ${cardClass} cursor-pointer transition-all duration-300 group relative z-10" onclick="selecionarVoz('${v.shortName}')">
                <div class="flex items-center gap-4">
                    <div class="w-12 h-12 rounded-full bg-zinc-900 border border-zinc-700/50 flex items-center justify-center group-hover:scale-110 transition-transform shadow-inner">
                        <i class="fa-solid ${iconClass} text-xl drop-shadow-md"></i>
                    </div>
                    <div>
                        <p class="text-base font-bold text-white group-hover:text-purple-300 transition-colors">${nomeDisplay}</p>
                        <div class="flex items-center gap-2 mt-1">
                            ${genderTag}
                        </div>
                    </div>
                </div>
                <button class="w-10 h-10 rounded-full bg-zinc-800 border border-zinc-700/50 flex items-center justify-center text-zinc-400 hover:bg-emerald-500 hover:text-white hover:border-emerald-400 transition-all shadow-md group-hover:border-purple-500/30" onclick="tocarPreview(event, '${v.shortName}')">
                    <i id="play_icon_${v.shortName}" class="fa-solid fa-play text-sm ml-0.5"></i>
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
            body: JSON.stringify({ texto: "Olá, sou uma voz neural da sua plataforma. Esta é a minha qualidade de narração.", voz: shortName, velocidade: 1.0, pitch: 0, volume: 0 }) 
        });
        
        const dados = await res.json();
        if(dados.status === "erro") throw new Error(dados.mensagem);

        playerPreview.src = "data:audio/mp3;base64," + dados.audio_base64;
        playerPreview.play();
        
        playerPreview.onended = () => { icon.className = "fa-solid fa-play text-sm ml-0.5"; };
    } catch(e) {
        alert("Erro no Preview: " + e.message);
        icon.className = "fa-solid fa-play text-sm ml-0.5"; 
    } 
}

// -----------------------------------------------------
// NOVA FUNÇÃO BLINDADA COM COBRANÇA E ATUALIZAÇÃO DE SALDO
// -----------------------------------------------------
async function gerarAudioCompleto() {
    const btn = document.getElementById('btn_gerar_voz');
    const txtBtn = document.getElementById('txt_btn_voz') || btn.querySelector('span'); // Pega o span correto
    const texto = document.getElementById('texto_voz').value;
    const playerContainer = document.getElementById('player_container');
    
    if(!texto.trim()) return alert("Digite um texto antes de sintetizar!");

    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    if (txtBtn) txtBtn.innerHTML = `Gravando na Nuvem... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;
    
    playerContainer.classList.remove('hidden');
    playerContainer.innerHTML = `<p class="text-purple-400 animate-pulse text-center font-bold text-sm"><i class="fa-solid fa-microphone-lines fa-fade mr-2"></i> O estúdio neural está gravando a sua locução... (-30 Coins)</p>`;

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
        
        if(!res.ok) {
            let erroReal = "Erro no servidor.";
            try { const dadosErro = await res.json(); erroReal = dadosErro.detail || erroReal; } catch(e) {}
            throw new Error(erroReal);
        }
        
        const dados = await res.json();

        // ==========================================
        // MAGIA DO FRONT-END: Atualiza o Saldo Dinâmico
        // ==========================================
        if(dados.novo_saldo !== undefined) {
            const paineisDeCoins = document.querySelectorAll('.fa-coins');
            paineisDeCoins.forEach(icone => {
                const elementoPai = icone.closest('p'); 
                if(elementoPai) {
                    const textoSaldo = dados.novo_saldo.toLocaleString('pt-BR');
                    elementoPai.innerHTML = `<i class="fa-solid fa-coins"></i> ${textoSaldo} coins`;
                    
                    // Pisca em roxo para indicar a ação do Voice Synth
                    elementoPai.classList.add('text-purple-400', 'scale-110');
                    setTimeout(() => elementoPai.classList.remove('text-purple-400', 'scale-110'), 500);
                }
            });
        }
        // ==========================================

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
        // Tratamento especial para saldo insuficiente
        const isCoinError = e.message.includes('Coins insuficientes');
        const erroClass = isCoinError ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20';
        playerContainer.innerHTML = `<div class="${erroClass} border p-4 rounded-lg text-center font-bold text-sm"><i class="fa-solid fa-triangle-exclamation mb-2 text-2xl block"></i> ${e.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        if (txtBtn) txtBtn.innerText = "Sintetizar Voz Neural (30 Coins)";
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
