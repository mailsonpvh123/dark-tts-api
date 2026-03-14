// ==========================================
// CONFIGURAÇÕES GLOBAIS
// ==========================================
const URL_API_VOZES = "/vozes"; 
const URL_API_DIRETA = "/gerar_narracao"; 
let vozesData = [];
let vozSelecionada = "pt-BR-AntonioNeural"; 
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
                    <br><span class="text-sm font-bold">Erro de Conexão</span>
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
// FUNÇÕES DE INTERFACE (VOZES E ABAS)
// ==========================================
function alternarAbaVozes(tipo) {
    abaVozAtiva = tipo;
    
    const btnPadrao = document.getElementById('aba_btn_padrao');
    const btnPremium = document.getElementById('aba_btn_premium');
    
    if (tipo === 'padrao') {
        btnPadrao.className = "flex-1 py-2 text-xs font-bold rounded-md bg-zinc-800 text-white shadow-sm transition-all";
        btnPremium.className = "flex-1 py-2 text-xs font-bold rounded-md text-zinc-500 hover:text-white transition-all";
        const primeiraPadrao = vozesData.find(v => v.tipo === 'padrao');
        if(primeiraPadrao) selecionarVoz(primeiraPadrao.shortName);
    } else {
        btnPremium.className = "flex-1 py-2 text-xs font-bold rounded-md bg-zinc-800 text-yellow-500 shadow-sm transition-all";
        btnPadrao.className = "flex-1 py-2 text-xs font-bold rounded-md text-zinc-500 hover:text-white transition-all";
        const primeiraPremium = vozesData.find(v => v.tipo === 'premium');
        if(primeiraPremium) selecionarVoz(primeiraPremium.shortName);
    }
    
    renderizarListaVozes();
}

function renderizarListaVozes() {
    const container = document.getElementById('lista_vozes');
    if(!container) return;
    container.innerHTML = '';
    
    const vozesFiltradas = vozesData.filter(v => v.tipo === abaVozAtiva);
    
    vozesFiltradas.forEach(v => {
        let isSelected = v.shortName === vozSelecionada;
        let isPremium = v.tipo === 'premium';

        let baseClass = isPremium ? "bg-amber-500/5 hover:border-amber-500/40" : "bg-[#09090b] hover:border-purple-500/40 hover:bg-purple-500/5";
        let cardClass = isSelected 
            ? "border-emerald-500 bg-emerald-500/10 shadow-[0_0_20px_rgba(16,185,129,0.15)]" 
            : `border-zinc-800 ${baseClass}`;
            
        let iconClass = isPremium ? 'fa-gem text-amber-400' : (v.gender === 'Female' ? 'fa-face-smile-beam text-pink-400' : 'fa-user-astronaut text-blue-400');
        
        let tagsHtml = isPremium 
            ? '<span class="text-[10px] font-bold text-yellow-400 bg-yellow-500/10 px-2 py-0.5 rounded border border-yellow-500/20"><i class="fa-solid fa-bolt"></i> Premium</span>'
            : (v.gender === 'Female' 
                ? '<span class="text-[10px] font-bold text-pink-400 bg-pink-500/10 px-2 py-0.5 rounded border border-pink-500/20">Feminino</span>'
                : '<span class="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">Masculino</span>');

        let nomeDisplay = v.shortName.replace(/Neural/ig, '').replace(/Multilingual/ig, '').replace(/V2/ig, '').trim(); 
        let partes = v.shortName.split('-');
        
        if (isPremium) {
            nomeDisplay = v.name; 
        } else if (partes.length >= 3) {
            let idiomaCodigo = partes[0].toLowerCase();
            let regiaoCodigo = partes[1].toUpperCase();
            let nomeAtor = partes.slice(2).join(' ').replace(/Neural|Multilingual|V2/ig, '').trim();
            nomeDisplay = `${nomeAtor} - ${idiomaCodigo.toUpperCase()}-${regiaoCodigo}`;
        }

        container.innerHTML += `
            <div class="flex items-center justify-between p-4 rounded-xl border ${cardClass} cursor-pointer transition-all duration-300 group relative z-10" onclick="selecionarVoz('${v.shortName}')">
                <div class="flex items-center gap-4">
                    <div class="w-10 h-10 rounded-full bg-zinc-900 border border-zinc-700/50 flex items-center justify-center group-hover:scale-110 transition-transform shadow-inner shrink-0">
                        <i class="fa-solid ${iconClass} text-lg drop-shadow-md"></i>
                    </div>
                    <div>
                        <p class="text-[13px] font-bold text-white group-hover:text-purple-300 transition-colors leading-tight mb-1">${nomeDisplay}</p>
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
    
    const painelEdge = document.getElementById('controles_edge');
    const painelGemini = document.getElementById('controles_gemini');
    
    if(sn.includes("gemini-premium")) {
        painelEdge.classList.add('hidden');
        painelGemini.classList.remove('hidden');
    } else {
        painelGemini.classList.add('hidden');
        painelEdge.classList.remove('hidden');
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
        
        const isPremium = vozSelecionada.includes("gemini-premium");
        
        if(contador) {
            if(isPremium) {
                // NOVA LÓGICA DE CHUNKING NO FRONT-END
                if(tamanho > 4000) {
                    const chunks = Math.ceil(tamanho / 4000);
                    contador.innerHTML = `<i class="fa-solid fa-layer-group text-yellow-500"></i> ${tamanho} chars (${chunks} Partes Automáticas)`;
                    contador.classList.replace('text-zinc-500', 'text-yellow-400');
                    contador.classList.replace('border-zinc-700', 'border-yellow-500/50');
                    contador.classList.remove('text-red-400', 'border-red-500/50');
                } else {
                    contador.innerText = `${tamanho} caracteres (Premium)`;
                    contador.classList.replace('text-yellow-400', 'text-zinc-500');
                    contador.classList.replace('border-yellow-500/50', 'border-zinc-700');
                    contador.classList.remove('text-red-400', 'border-red-500/50');
                }
            } else {
                contador.innerText = `${tamanho} caracteres`;
                contador.classList.replace('text-yellow-400', 'text-zinc-500');
                contador.classList.replace('border-yellow-500/50', 'border-zinc-700');
                contador.classList.remove('text-red-400', 'border-red-500/50');
            }
        }

        if(btnTxt) {
            if(!isPremium) {
                btnTxt.innerHTML = `Sintetizar Voz Padrão (30 Coins)`;
                document.getElementById('btn_gerar_voz').className = "w-full mt-6 bg-purple-600 hover:bg-purple-500 text-white font-bold py-4 px-4 rounded-xl shadow-[0_0_20px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center gap-2 group border border-purple-500/50 relative z-10";
            } else {
                let custo = Math.ceil((tamanho / 900.0) * 10);
                if (custo < 1) custo = 1;
                btnTxt.innerHTML = `Sintetizar Voz Premium (<span class="text-yellow-900 drop-shadow-md">${custo} Coins</span>)`;
                document.getElementById('btn_gerar_voz').className = "w-full mt-6 bg-yellow-500 hover:bg-yellow-400 text-yellow-900 font-black py-4 px-4 rounded-xl shadow-[0_0_20px_rgba(234,179,8,0.3)] transition-all flex items-center justify-center gap-2 group border border-yellow-400 relative z-10";
            }
        }
    }, 300); 
}

// ==========================================
// CONTROLES DE SLIDERS
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

function ajustarTemperatura(delta) {
    const slider = document.getElementById('gemini_temperatura');
    let newVal = parseFloat(slider.value) + delta;
    if(newVal > 2.0) newVal = 2.0;
    if(newVal < 0.0) newVal = 0.0;
    slider.value = newVal.toFixed(1);
    document.getElementById('val_temp').innerText = slider.value;
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
        const res = await fetch(URL_API_DIRETA, { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ 
                texto: "Olá, sou uma voz neural da sua plataforma. Esta é a minha qualidade de narração.", 
                voz: shortName, 
                velocidade: 1.0, 
                pitch: 0, 
                temperatura: 1.0 
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
    
    if(!texto.trim()) return alert("Digite um texto antes de sintetizar!");

    const textoBotaoOriginal = txtBtn.innerHTML;
    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    txtBtn.innerHTML = `Sintetizando... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;
    
    playerContainer.classList.remove('hidden');
    
    // Mostra pro usuário que o áudio pode demorar mais se for dividido
    const isPremium = vozSelecionada.includes("gemini-premium");
    let msgExtra = (isPremium && texto.length > 4000) ? "<br><span class='text-[10px] text-zinc-500'>O texto é longo e está sendo dividido e costurado em segundo plano. Aguarde.</span>" : "";
    
    playerContainer.innerHTML = `<p class="text-purple-400 animate-pulse text-center font-bold text-sm"><i class="fa-solid fa-microphone-lines fa-fade mr-2"></i> O estúdio neural está gravando a sua locução...${msgExtra}</p>`;

    const payload = { 
        texto: texto, 
        voz: vozSelecionada, 
        velocidade: parseFloat(document.getElementById('velocidade').value), 
        pitch: parseInt(document.getElementById('pitch').value),
        volume: 0,
        temperatura: parseFloat(document.getElementById('gemini_temperatura') ? document.getElementById('gemini_temperatura').value : 1.0),
        instrucao_estilo: document.getElementById('gemini_prompt') ? document.getElementById('gemini_prompt').value : ""
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

        if(dados.novo_saldo !== undefined) {
            const paineisDeCoins = document.querySelectorAll('.fa-coins');
            paineisDeCoins.forEach(icone => {
                const elementoPai = icone.closest('p'); 
                if(elementoPai) {
                    elementoPai.innerHTML = `<i class="fa-solid fa-coins"></i> ${dados.novo_saldo.toLocaleString('pt-BR')} coins`;
                    elementoPai.classList.add('text-purple-400', 'scale-110');
                    setTimeout(() => elementoPai.classList.remove('text-purple-400', 'scale-110'), 500);
                }
            });
        }

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
        const isCoinError = e.message.includes('Coins insuficientes');
        const erroClass = isCoinError ? 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20' : 'text-red-400 bg-red-500/10 border-red-500/20';
        playerContainer.innerHTML = `<div class="${erroClass} border p-4 rounded-lg text-center font-bold text-sm"><i class="fa-solid fa-triangle-exclamation mb-2 text-2xl block"></i> ${e.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        recalcularCustoVoz();
    }
}

// ... [O restante do seu código utilitário de paraphraser permanece inalterado logo abaixo] ...
function contarPalavrasLocal(texto) {
    if (!texto || texto.trim() === "") return 0;
    return texto.trim().split(/\s+/).length;
}

async function transmutarTexto() {
    const inputTexto = document.getElementById('texto_original');
    if(!inputTexto) return;
    
    const textoOrig = inputTexto.value;
    const elEstrategia = document.getElementById('estrategia_escrita');
    const modoSelecionado = elEstrategia && elEstrategia.value.toLowerCase().includes('reddit') ? 'reddit' : 'padrao';
    
    const elCanal = document.getElementById('nome_canal'); 
    const nomeCanal = elCanal ? elCanal.value : "";

    const elGancho = document.getElementById('gancho_exato'); 
    const tituloGancho = elGancho ? elGancho.value : "";
    
    if (!textoOrig.trim()) return alert("Cole o texto original primeiro!");

    const painelResultado = document.getElementById('texto_transmutado');
    const btnTexto = document.getElementById('txt_btn_transmutar');
    
    painelResultado.value = "Gerando a história com a inteligência do Gemini... Por favor, aguarde.";
    btnTexto.innerHTML = `Transmutando... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;

    try {
        const payload = {
            texto: textoOrig,
            tom: "Sarcástico e Ácido",
            idioma: "Português (Brasil)",
            modo: modoSelecionado,
            gancho_exato: tituloGancho,
            nome_canal: nomeCanal
        };

        const res = await fetch('/api/v1/paraphraser', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const dados = await res.json();
        console.log("Resposta recebida da API:", dados);

        if (!res.ok) throw new Error(dados.detail || "Erro no servidor.");

        const textoGerado = dados.texto_parafrazedo || dados.texto_parafraseado || dados.texto;

        if (!textoGerado) {
            throw new Error("Falha na formatação da resposta da API.");
        }

        painelResultado.value = textoGerado;
        
        // AUTO-SAVE DO RESULTADO FINAL GERADO PELA IA
        localStorage.setItem('paraph_resultado', textoGerado);
        
        const contadorRes = document.getElementById('contador_resultado');
        if(contadorRes) {
            contadorRes.innerText = contarPalavrasLocal(textoGerado) + " palavras";
        }
        
        if(dados.novo_saldo !== undefined) {
            const paineisDeCoins = document.querySelectorAll('.fa-coins');
            paineisDeCoins.forEach(icone => {
                const elementoPai = icone.closest('p'); 
                if(elementoPai) {
                    elementoPai.innerHTML = `<i class="fa-solid fa-coins"></i> ${dados.novo_saldo.toLocaleString('pt-BR')} coins`;
                    elementoPai.classList.add('text-pink-400', 'scale-110');
                    setTimeout(() => elementoPai.classList.remove('text-pink-400', 'scale-110'), 500);
                }
            });
        }

    } catch (e) {
        painelResultado.value = `Erro Técnico: ${e.message}`;
    } finally {
        btnTexto.innerText = "Transmutar Texto (25 Coins)";
    }
}
