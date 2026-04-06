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
            if (path === '/audio-mixer') icon.classList.add('text-amber-400');
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

function despacharParaVoice(idCampoOrigem) {
    const texto = document.getElementById(idCampoOrigem).value;
    if(!texto || texto.trim() === "") return alert("Aviso: O texto está vazio!"); 
    localStorage.setItem('texto_pendente_voice', texto);
    window.location.href = '/voice-synthesizer'; 
}

// ==========================================
// FUNÇÕES DO CLIP HUNTER (MINERADOR DE MÍDIAS)
// ==========================================
async function buscarMidiaHunter() {
    const termoInput = document.getElementById('hunter_input');
    const galeria = document.getElementById('hunter_galeria');
    const btn = document.getElementById('hunter_btn');
    const status = document.getElementById('hunter_status');
    const mediaType = document.getElementById('hunter_type').value;
    const orientation = document.getElementById('hunter_orientation').value;
    
    if(!termoInput || !galeria) return;
    
    const termo = termoInput.value.trim();
    if(termo === "") return alert("Por favor, insira um termo para buscar!");

    if(window.hunterAudioAtual) {
        window.hunterAudioAtual.pause();
        window.hunterAudioUrlAtual = null;
    }

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
    status.innerText = "Minerando arquivos na nuvem...";
    galeria.innerHTML = ""; 
    
    try {
        const resposta = await fetch(`/api/cliphunter/search?query=${encodeURIComponent(termo)}&media_type=${mediaType}&orientation=${orientation}`);
        const dados = await resposta.json();
        
        if(!resposta.ok) throw new Error(dados.detail || "Erro ao conectar na API.");
        
        if(dados.results.length === 0) {
            galeria.innerHTML = `<div class="col-span-full text-center py-10 text-zinc-500"><i class="fa-solid fa-ghost text-4xl mb-3"></i><p>Nenhuma mídia encontrada para "${termo}". Tente outro termo em inglês.</p></div>`;
            status.innerText = "Busca concluída (0 resultados).";
            return;
        }

        status.innerText = `Mostrando resultados para "${dados.query_traduzida}" (${dados.results.length} mídias)`;
        
        dados.results.forEach(item => {
            const card = document.createElement('div');
            card.className = "bg-[#1E1E1E] rounded-xl border border-zinc-800 overflow-hidden hover:border-emerald-500/50 transition-all shadow-lg flex flex-col";
            
            let conteudoVisual = "";
            let btnAcao = "";
            
            if(item.type === "video") {
                conteudoVisual = `
                    <div class="relative aspect-video bg-black group">
                        <img src="${item.thumb}" class="w-full h-full object-cover opacity-80 group-hover:opacity-50 transition-opacity">
                        <button onclick="abrirPreviewHunter('${item.url}', 'video')" class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <i class="fa-solid fa-circle-play text-5xl text-emerald-400 drop-shadow-lg scale-90 group-hover:scale-100 transition-transform"></i>
                        </button>
                        <span class="absolute bottom-2 right-2 bg-black/80 px-2 py-1 text-[10px] rounded text-white font-bold">${item.duration}s</span>
                    </div>`;
                btnAcao = `<a href="${item.url}" target="_blank" download class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-2 text-center text-sm rounded transition-colors"><i class="fa-solid fa-download mr-1"></i> Baixar</a>`;
            } 
            else if(item.type === "image") {
                conteudoVisual = `
                    <div class="relative aspect-square bg-black group">
                        <img src="${item.thumb}" class="w-full h-full object-cover opacity-90 group-hover:opacity-60 transition-opacity">
                        <button onclick="abrirPreviewHunter('${item.url}', 'image')" class="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                            <i class="fa-solid fa-expand text-4xl text-zinc-200 drop-shadow-lg scale-90 group-hover:scale-100 transition-transform"></i>
                        </button>
                    </div>`;
                btnAcao = `<a href="${item.url}" target="_blank" download class="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold py-2 text-center text-sm rounded transition-colors"><i class="fa-solid fa-download mr-1"></i> Baixar</a>`;
            }
            else if(item.type === "audio") {
                conteudoVisual = `
                    <div class="p-4 bg-zinc-900 border-b border-zinc-800 flex items-center justify-center h-24">
                        <button onclick="tocarAudioHunter(this, '${item.url}')" class="w-12 h-12 rounded-full bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-500 hover:bg-amber-500 hover:text-white transition-colors shadow-lg">
                            <i class="fa-solid fa-play text-lg ml-1"></i>
                        </button>
                    </div>`;
                btnAcao = `<a href="${item.url}" target="_blank" download class="w-full bg-amber-600 hover:bg-amber-500 text-white font-bold py-2 text-center text-sm rounded transition-colors"><i class="fa-solid fa-download mr-1"></i> Baixar</a>`;
            }

            card.innerHTML = `
                ${conteudoVisual}
                <div class="p-3 flex-1 flex flex-col justify-between">
                    <p class="text-[11px] text-zinc-400 mb-3 truncate" title="${item.author || item.title}"><i class="fa-solid ${item.type === 'audio' ? 'fa-music' : 'fa-camera'} mr-1"></i> ${item.author || item.title}</p>
                    ${btnAcao}
                </div>
            `;
            galeria.appendChild(card);
        });

    } catch(erro) {
        status.innerText = "Falha na mineração.";
        galeria.innerHTML = `<div class="col-span-full text-center py-10 text-red-400 font-bold border border-red-500/30 bg-red-500/10 rounded-xl"><i class="fa-solid fa-triangle-exclamation mb-2 text-2xl"></i><br>${erro.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<i class="fa-solid fa-magnifying-glass"></i> Minerar Mídias';
    }
}

function abrirPreviewHunter(url, type) {
    if(window.hunterAudioAtual) {
        window.hunterAudioAtual.pause();
        window.hunterAudioUrlAtual = null;
        document.querySelectorAll('#hunter_galeria .fa-pause').forEach(i => {
            i.classList.remove('fa-pause');
            i.classList.add('fa-play');
        });
    }

    const modal = document.getElementById('hunter_modal');
    const content = document.getElementById('hunter_modal_content');
    
    if(type === 'video') {
        content.innerHTML = `<video controls autoplay class="max-w-full max-h-[85vh] rounded-xl shadow-2xl outline-none border border-zinc-700"><source src="${url}" type="video/mp4"></video>`;
    } else if (type === 'image') {
        content.innerHTML = `<img src="${url}" class="max-w-full max-h-[85vh] rounded-xl shadow-2xl object-contain border border-zinc-700">`;
    }
    
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function fecharModalHunter() {
    const modal = document.getElementById('hunter_modal');
    const content = document.getElementById('hunter_modal_content');
    
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    content.innerHTML = ''; 
}

function tocarAudioHunter(btn, url) {
    if(window.hunterAudioAtual) {
        window.hunterAudioAtual.pause();
        
        document.querySelectorAll('#hunter_galeria .fa-pause').forEach(i => {
            i.classList.remove('fa-pause');
            i.classList.add('fa-play');
        });
        
        if (window.hunterAudioUrlAtual === url) {
            window.hunterAudioUrlAtual = null; 
            return; 
        }
    }
    
    const icon = btn.querySelector('i');
    
    window.hunterAudioAtual = new Audio(url);
    window.hunterAudioUrlAtual = url;
    window.hunterAudioAtual.play();
    
    icon.classList.remove('fa-play');
    icon.classList.add('fa-pause');
    
    window.hunterAudioAtual.onended = () => {
        icon.classList.remove('fa-pause');
        icon.classList.add('fa-play');
        window.hunterAudioUrlAtual = null;
    };
}

// ==========================================
// FUNÇÕES DO PARAPHRASER (TEXT TRANSMUTER)
// ==========================================
async function transmutarTexto() {
    const txtOriginal = document.getElementById('texto_original').value;
    const modo = document.getElementById('estrategia_escrita').value;
    const nomeCanal = document.getElementById('nome_canal').value;
    const ganchoExato = document.getElementById('gancho_exato').value;
    const btn = document.getElementById('btn_transmutar');
    const txtBtn = document.getElementById('txt_btn_transmutar');
    const txtResultado = document.getElementById('texto_transmutado');
    const contadorResultado = document.getElementById('contador_resultado');

    if (!txtOriginal || txtOriginal.trim() === "") {
        return alert("Por favor, cole o texto original antes de transmutar!");
    }

    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    const textoOriginalBotao = txtBtn.innerHTML;
    txtBtn.innerHTML = `Transmutando... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;
    txtResultado.value = "Os deuses da IA estão reescrevendo e blindando seu texto. Isso pode levar alguns segundos...";

    const payload = {
        texto: txtOriginal,
        modo: modo,
        nome_canal: nomeCanal,
        gancho_exato: ganchoExato,
        tom: "Sarcástico e Ácido", 
        idioma: "Português (Brasil)"
    };

    try {
        const res = await fetch("/api/v1/paraphraser", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        const dados = await res.json();
        
        if(!res.ok) {
            throw new Error(dados.detail || "Erro na comunicação com a IA.");
        }
        
        txtResultado.value = dados.texto_parafrazedo;
        
        if(typeof contarPalavrasLocal === 'function' && contadorResultado) {
            contadorResultado.innerText = contarPalavrasLocal(dados.texto_parafrazedo) + ' palavras';
        }
        
        localStorage.setItem('paraph_resultado', dados.texto_parafrazedo);

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

    } catch (e) {
        const isCoinError = e.message.includes('Coins insuficientes');
        if (isCoinError) {
            txtResultado.value = `[ERRO DE SALDO]\n\n${e.message}`;
        } else {
            txtResultado.value = `[FALHA NA TRANSMUTAÇÃO]\n\nOcorreu um erro no servidor:\n${e.message}`;
        }
    } finally {
        btn.disabled = false;
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        txtBtn.innerHTML = textoOriginalBotao;
    }
}

// ==========================================
// FUNÇÕES DA INTERFACE DO ESTÚDIO DE DUBLAGEM (VOICE SYNTH)
// ==========================================
function alternarAbaVozes(tipo) {
    abaVozAtiva = tipo;
    
    const panelStd = document.getElementById('controles_standard');
    const panelCre = document.getElementById('controles_creator');
    const panelCin = document.getElementById('controles_cinematic');
    
    if(panelStd) panelStd.classList.add('hidden');
    if(panelCre) panelCre.classList.add('hidden');
    if(panelCin) panelCin.classList.add('hidden');
    
    const btnPadrao = document.getElementById('aba_btn_padrao');
    const btnCreator = document.getElementById('aba_btn_creator');
    const btnCinematic = document.getElementById('aba_btn_cinematic');
    
    [btnPadrao, btnCreator, btnCinematic].forEach(btn => {
        if(btn) btn.className = "flex-1 py-2 text-xs font-bold rounded-lg text-zinc-500 hover:text-white transition-all";
    });
    
    if (tipo === 'padrao') {
        if(btnPadrao) btnPadrao.className = "flex-1 py-2 text-xs font-bold rounded-lg bg-zinc-800 text-white shadow-sm transition-all border border-zinc-700/50";
        atualizarInfoTier("Qualidade Standard", "Vozes sintéticas de alta eficiência. Ideais para testes ou canais com alto volume de postagem.");
        if(panelStd) panelStd.classList.remove('hidden');
    } else if (tipo === 'creator') {
        if(btnCreator) btnCreator.className = "flex-1 py-2 text-xs font-bold rounded-lg bg-zinc-800 text-blue-400 shadow-sm transition-all border border-zinc-700/50";
        atualizarInfoTier("Qualidade Creator (Gemini TTS)", "Vozes neurais naturais e emocionais. Focado em alta retenção e Storytelling.");
        if(panelCre) panelCre.classList.remove('hidden');
    } else if (tipo === 'cinematic') {
        if(btnCinematic) btnCinematic.className = "flex-1 py-2 text-xs font-bold rounded-lg bg-amber-500/20 text-amber-400 shadow-sm transition-all border border-amber-500/50";
        atualizarInfoTier("Qualidade Cinematic (ElevenLabs)", "Qualidade Ultra-Realista de cinema. Perfeito para documentários densos.");
        if(panelCin) panelCin.classList.remove('hidden');
    }
    
    const primeiraDaLista = vozesData.find(v => v.tipo === tipo);
    if(primeiraDaLista) selecionarVoz(primeiraDaLista.shortName);
    
    renderizarListaVozes();
}

function atualizarInfoTier(titulo, desc) {
    const infoContainer = document.getElementById('info_tier');
    if(!infoContainer) return;
    
    infoContainer.innerHTML = `
        <div class="bg-zinc-800/50 border border-zinc-700 p-4 rounded-lg shadow-inner mt-4 relative z-10">
            <p class="text-xs font-bold text-white mb-1"><i class="fa-solid fa-circle-info text-purple-400 mr-1"></i> ${titulo}</p>
            <p class="text-[11px] text-zinc-400 leading-relaxed">${desc}</p>
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
            
        let isFemale = v.gender && (v.gender.includes('Female') || v.gender.includes('Feminino'));
        let iconClass = isCinematic ? 'fa-star text-amber-400' : (isCreator ? 'fa-clapperboard text-blue-400' : (isFemale ? 'fa-face-smile-beam text-pink-400' : 'fa-user-astronaut text-purple-400'));
        
        let tagsHtml = "";
        if (isCinematic) tagsHtml = '<span class="text-[10px] font-bold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">Cinematic</span>';
        else if (isCreator) tagsHtml = '<span class="text-[10px] font-bold text-blue-400 bg-blue-500/10 px-2 py-0.5 rounded border border-blue-500/20">Creator</span>';
        else tagsHtml = (isFemale ? '<span class="text-[10px] font-bold text-pink-400 bg-pink-500/10 px-2 py-0.5 rounded border border-pink-500/20">Feminino</span>' : '<span class="text-[10px] font-bold text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20">Masculino</span>');

        let nomeDisplay = v.name;
        if (!isCinematic && !isCreator) {
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
                        <p class="text-[10px] text-zinc-500 font-mono">${v.gender || ''} | ${v.desc || ''}</p>
                    </div>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                    <button class="w-8 h-8 rounded-full bg-zinc-800 border border-zinc-700/50 flex items-center justify-center text-zinc-400 hover:bg-emerald-500 hover:text-white hover:border-emerald-400 transition-all shadow-md shrink-0" title="Ouvir Prévia" onclick="tocarPreview(event, '${v.shortName}')">
                        <i id="play_icon_${v.shortName}" class="fa-solid fa-play text-xs ml-0.5"></i>
                    </button>
                    ${isSelected ? '<i class="fa-solid fa-circle-check text-emerald-500 text-lg"></i>' : '<i class="fa-solid fa-circle text-zinc-800 group-hover:text-zinc-600 transition-colors text-lg"></i>'}
                </div>
            </div>`;
    });
}

function selecionarVoz(sn) { 
    if(window.playerPreviewAtual) { 
        window.playerPreviewAtual.pause(); 
        window.playerPreviewAtual = null; 
        document.querySelectorAll('[id^="play_icon_"]').forEach(i => i.className = 'fa-solid fa-play text-xs ml-0.5'); 
    }
    vozSelecionada = sn; 
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

function ajustarSlider(idInput, idLabel, delta, min, max, suffix) {
    const el = document.getElementById(idInput);
    if(!el) return;
    let newVal = parseFloat(el.value) + delta;
    if (newVal < min) newVal = min;
    if (newVal > max) newVal = max;
    
    if (Number.isInteger(min) && Number.isInteger(max) && Number.isInteger(delta)) {
        el.value = Math.round(newVal);
        document.getElementById(idLabel).innerText = el.value + suffix;
    } else {
        el.value = newVal.toFixed(1);
        document.getElementById(idLabel).innerText = el.value + suffix;
    }
}

async function tocarPreview(event, shortName) {
    event.stopPropagation();
    
    if (window.playerPreviewAtual) {
        window.playerPreviewAtual.pause();
        document.querySelectorAll('[id^="play_icon_"]').forEach(i => i.className = "fa-solid fa-play text-xs ml-0.5");
    }

    const icon = document.getElementById(`play_icon_${shortName}`);
    if(icon) icon.className = "fa-solid fa-circle-notch fa-spin text-white"; 
    
    try {
        const audioUrl = `/static/audios/previews/${shortName}.mp3`;
        const playerPreview = new Audio(audioUrl);
        window.playerPreviewAtual = playerPreview; 
        
        await playerPreview.play();
        if(icon) icon.className = "fa-solid fa-volume-high text-xs ml-0.5 text-emerald-400"; 
        
        playerPreview.onended = () => { 
            if(icon) icon.className = "fa-solid fa-play text-xs ml-0.5"; 
        };

    } catch(e) {
        alert(`Arquivo de prévia não encontrado!\n\n(Certifique-se de que baixou e enviou para /static/audios/previews/${shortName}.mp3 no painel)`);
        if(icon) icon.className = "fa-solid fa-play text-xs ml-0.5 text-red-500"; 
    } 
}

// ==========================================
// FUNÇÕES DE EXPORTAÇÃO E SRT
// ==========================================
function baixarSRT() {
    if(!srtGlobal || srtGlobal.trim() === "") return alert("A legenda (SRT) ainda não está disponível. Gere o áudio primeiro.");
    const blob = new Blob([srtGlobal], { type: 'text/plain' });
    const link = document.createElement('a'); 
    link.href = URL.createObjectURL(blob);
    link.download = `Legenda_${new Date().getTime()}.srt`;
    link.click();
}

function enviarParaMetaSEO() {
    const roteiro = document.getElementById('texto_voz').value;
    if (!roteiro) return alert("O Roteiro está vazio.");
    
    let conteudoFinal = `ROTEIRO COMPLETO:\n${roteiro}\n\n`;
    
    if (srtGlobal && srtGlobal.trim() !== "") {
        conteudoFinal += `TIMELINE EXATA (USE PARA GERAR OS CAPÍTULOS NO YOUTUBE):\n${srtGlobal}`;
    }
    
    sessionStorage.setItem('seo_conteudo', conteudoFinal);
    window.location.href = '/meta-seo';
}

async function gerarAudioCompleto() {
    const btn = document.getElementById('btn_gerar_voz');
    const txtBtn = document.getElementById('txt_btn_voz');
    const texto = document.getElementById('texto_voz').value;
    const playerContainer = document.getElementById('player_container');
    
    if(!texto.trim()) return alert("Digite um texto antes de sintetizar!");

    const isCinematic = vozSelecionada.includes("cinematic-");
    const isCreator = vozSelecionada.includes("creator-");

    let velocidade = 1.0;
    if (abaVozAtiva === 'padrao') {
        velocidade = parseFloat(document.getElementById('velocidade_std')?.value || 1.0);
    } else if (abaVozAtiva === 'cinematic') {
        velocidade = parseFloat(document.getElementById('velocidade_cin')?.value || 1.0);
    }
    
    const pitch = abaVozAtiva === 'padrao' ? parseInt(document.getElementById('pitch_std')?.value || 0) : 0;
    const temperatura = parseFloat(document.getElementById('temperatura')?.value || 0.7);
    const estabilidade = parseFloat(document.getElementById('estabilidade')?.value || 0.5);
    const similaridade = parseFloat(document.getElementById('similaridade')?.value || 0.75);

    btn.disabled = true;
    btn.classList.add('opacity-70', 'cursor-not-allowed');
    
    txtBtn.innerHTML = `Processando no Estúdio... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;
    playerContainer.classList.remove('hidden');
    
    let icone = isCinematic ? "fa-star text-amber-400" : (isCreator ? "fa-clapperboard text-blue-400" : "fa-microphone-lines text-purple-400");
    let msgExtra = texto.length > 4000 ? "<br><span class='text-[10px] text-zinc-500'>O roteiro longo está sendo renderizado por partes para manter a qualidade.</span>" : "";
    
    playerContainer.innerHTML = `<p class="animate-pulse text-center font-bold text-sm bg-[#121214] p-4 rounded-xl border border-zinc-800"><i class="fa-solid ${icone} fa-fade mr-2"></i> Renderizando o seu áudio...${msgExtra}</p>`;

    const payload = { 
        texto: texto, 
        voz: vozSelecionada, 
        velocidade: velocidade, 
        pitch: pitch,
        temperatura: temperatura,
        estabilidade: estabilidade,
        similaridade: similaridade
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
        
        srtGlobal = dados.srt || "";

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
            
            <div class="flex flex-col sm:flex-row gap-3 border-t border-zinc-800/80 pt-4 mt-4">
                <button onclick="baixarSRT()" class="flex-1 bg-[#09090b] hover:bg-emerald-600 text-emerald-400 hover:text-white font-bold py-3.5 rounded-xl border border-emerald-500/30 hover:border-emerald-500 transition-all text-xs flex items-center justify-center gap-2 shadow-inner hover:shadow-[0_0_15px_rgba(16,185,129,0.4)] group">
                    <i class="fa-solid fa-download group-hover:-translate-y-1 transition-transform"></i> Baixar .SRT
                </button>
                <button onclick="enviarParaMetaSEO()" class="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-black py-3.5 rounded-xl border border-blue-500/50 transition-all text-xs flex items-center justify-center gap-2 shadow-[0_0_15px_rgba(59,130,246,0.4)] group">
                    <i class="fa-solid fa-rocket group-hover:translate-x-1 transition-transform"></i> Gerar Meta & SEO
                </button>
            </div>
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

// ==========================================
// MÓDULO: HISTÓRICO DE PRODUÇÃO
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

function mudarFiltroHistorico(ferramenta) {
    histFiltroAtual = ferramenta;
    histPaginaAtual = 1;
    
    document.querySelectorAll('.filtro-btn').forEach(btn => {
        btn.classList.remove('bg-emerald-500', 'text-white', 'shadow-[0_0_15px_rgba(16,185,129,0.3)]', 'border-emerald-400');
        btn.classList.add('bg-[#121214]', 'text-zinc-400', 'border-zinc-800');
    });

    let btnId = 'btn_filtro_todos';
    if(ferramenta.includes("Insights")) btnId = 'btn_filtro_insights';
    if(ferramenta.includes("Miner")) btnId = 'btn_filtro_miner';
    if(ferramenta.includes("Paraph")) btnId = 'btn_filtro_paraphraser';
    if(ferramenta.includes("Script")) btnId = 'btn_filtro_script';
    if(ferramenta.includes("Voice")) btnId = 'btn_filtro_voice';
    if(ferramenta.includes("SEO")) btnId = 'btn_filtro_seo';
    if(ferramenta.includes("Thumb")) btnId = 'btn_filtro_thumb';

    const btnAtivo = document.getElementById(btnId);
    if(btnAtivo) {
        btnAtivo.classList.remove('bg-[#121214]', 'text-zinc-400', 'border-zinc-800');
        btnAtivo.classList.add('bg-emerald-500', 'text-white', 'shadow-[0_0_15px_rgba(16,185,129,0.3)]', 'border-emerald-400');
    }

    carregarHistorico();
}

function mudarPaginaHistorico(delta) {
    histPaginaAtual += delta;
    carregarHistorico();
}

async function excluirRegistro(id) {
    if(!confirm("Tem certeza que deseja excluir permanentemente este registro da base de dados?")) return;
    
    try {
        const response = await fetch(`/api/v1/historico/${id}`, { method: 'DELETE' });
        if(response.ok) {
            carregarHistorico();
        } else {
            alert("Erro ao excluir registro.");
        }
    } catch(e) {
        alert("Falha na comunicação: " + e.message);
    }
}

function abrirModal(index) {
    const reg = histDadosAtuais[index];
    const modal = document.getElementById('modal_resultado');
    const conteudo = document.getElementById('modal_conteudo_interno');
    
    const titulo = document.getElementById('modal_titulo');
    const dataTxt = document.getElementById('modal_data');
    const iconeContainer = document.getElementById('modal_icone');
    const inputTxt = document.getElementById('modal_input');
    const outputContainer = document.getElementById('modal_output_container');
    const acoesContainer = document.getElementById('modal_acoes_container');

    titulo.innerText = reg.ferramenta;
    dataTxt.innerText = reg.data_formatada;
    inputTxt.innerText = reg.input_usuario;
    
    let iconeHtml = '<i class="fa-solid fa-code text-zinc-400"></i>';
    let bgGradient = 'from-zinc-500/20 to-zinc-600/20';
    let borderColor = 'border-zinc-500/30';
    
    if(reg.ferramenta.includes("Voice")) { iconeHtml = '<i class="fa-solid fa-microphone-lines text-purple-400 text-xl"></i>'; bgGradient = 'from-purple-500/20 to-fuchsia-600/20'; borderColor = 'border-purple-500/50'; }
    else if(reg.ferramenta.includes("Script")) { iconeHtml = '<i class="fa-solid fa-pen-nib text-orange-400 text-xl"></i>'; bgGradient = 'from-orange-500/20 to-red-600/20'; borderColor = 'border-orange-500/50'; }
    else if(reg.ferramenta.includes("Meta")) { iconeHtml = '<i class="fa-solid fa-magnifying-glass-chart text-blue-400 text-xl"></i>'; bgGradient = 'from-blue-500/20 to-indigo-600/20'; borderColor = 'border-blue-500/50'; }
    else if(reg.ferramenta.includes("Thumb")) { iconeHtml = '<i class="fa-solid fa-image text-rose-400 text-xl"></i>'; bgGradient = 'from-rose-500/20 to-pink-600/20'; borderColor = 'border-rose-500/50'; }
    else if(reg.ferramenta.includes("Gen")) { iconeHtml = '<i class="fa-solid fa-lightbulb text-yellow-400 text-xl"></i>'; bgGradient = 'from-yellow-400/20 to-amber-600/20'; borderColor = 'border-yellow-400/50'; }
    else if(reg.ferramenta.includes("Miner")) { iconeHtml = '<i class="fa-solid fa-magnet text-indigo-400 text-xl"></i>'; bgGradient = 'from-indigo-500/20 to-purple-600/20'; borderColor = 'border-indigo-500/50'; }
    else if(reg.ferramenta.includes("Paraph")) { iconeHtml = '<i class="fa-solid fa-rotate text-pink-400 text-xl"></i>'; bgGradient = 'from-pink-500/20 to-rose-600/20'; borderColor = 'border-pink-500/50'; }

    iconeContainer.className = `w-12 h-12 rounded-xl flex items-center justify-center shadow-lg border ${borderColor} bg-gradient-to-br ${bgGradient}`;
    iconeContainer.innerHTML = iconeHtml;

    acoesContainer.innerHTML = '';
    
    if (reg.ferramenta.includes("Voice")) {
        let pathAudio = reg.resultado;
        let srtTexto = "";

        if(pathAudio.includes("|SRT:")) {
             let partes = pathAudio.split("|SRT:");
             pathAudio = partes[0];
             srtTexto = partes[1];
        }

        outputContainer.innerHTML = `
            <div class="p-6 text-center">
                <i class="fa-solid fa-compact-disc fa-spin text-4xl text-purple-500/30 mb-4 inline-block"></i>
                <audio controls class="w-full mt-2 rounded-lg" src="${pathAudio}"></audio>
            </div>
        `;

        acoesContainer.innerHTML += `
            <a href="${pathAudio}" download class="col-span-1 py-3 bg-[#18181b] hover:bg-emerald-600 hover:border-emerald-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm text-center">
                <i class="fa-solid fa-download"></i> Baixar MP3
            </a>
        `;
        
        if(srtTexto) {
             acoesContainer.innerHTML += `
                 <button onclick="baixarSRTDireto(\`${srtTexto.replace(/`/g, "\\`")}\`)" class="col-span-1 py-3 bg-[#18181b] hover:bg-blue-600 hover:border-blue-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                     <i class="fa-solid fa-closed-captioning"></i> Baixar .SRT
                 </button>
             `;
        }

    } else {
        outputContainer.innerHTML = `<pre id="texto_resgate" class="text-sm text-zinc-300 font-mono whitespace-pre-wrap p-6 relative z-10 max-h-64 overflow-y-auto custom-scrollbar">${reg.resultado}</pre>`;
        
        acoesContainer.innerHTML = `
            <button onclick="copiarTextoHist()" class="col-span-1 py-3 bg-[#18181b] hover:bg-emerald-600 hover:border-emerald-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                <i class="fa-solid fa-copy"></i> Copiar
            </button>
            <button onclick="baixarTxtHist('${reg.ferramenta}', '${reg.data_formatada}')" class="col-span-1 py-3 bg-[#18181b] hover:bg-zinc-700 hover:border-zinc-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                <i class="fa-solid fa-file-arrow-down"></i> .TXT
            </button>
        `;

        if(reg.ferramenta.includes("Gen Insights")) {
             acoesContainer.innerHTML += `
                <button onclick="encaminharPara('script', ${index})" class="col-span-2 py-3 bg-[#18181b] hover:bg-orange-600 hover:border-orange-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                    <i class="fa-solid fa-pen-nib"></i> Enviar para Script Forge
                </button>
            `;
        } else if(reg.ferramenta.includes("Paraphraser")) {
             acoesContainer.innerHTML += `
                <button onclick="encaminharPara('voice', ${index})" class="col-span-2 py-3 bg-[#18181b] hover:bg-purple-600 hover:border-purple-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                    <i class="fa-solid fa-microphone-lines"></i> Enviar para Voice Synth
                </button>
            `;
        } else if(reg.ferramenta.includes("Script Forge")) {
             acoesContainer.innerHTML += `
                <button onclick="encaminharPara('voice', ${index})" class="col-span-1 py-3 bg-[#18181b] hover:bg-purple-600 hover:border-purple-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                    <i class="fa-solid fa-microphone"></i> Voice Synth
                </button>
                <button onclick="encaminharPara('seo', ${index})" class="col-span-1 py-3 bg-[#18181b] hover:bg-blue-600 hover:border-blue-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                    <i class="fa-solid fa-rocket"></i> Meta & SEO
                </button>
            `;
        }
    }

    // A MÁGICA: Além de remover o hidden, adiciona o flex para o grid funcionar!
    modal.classList.remove('hidden');
    modal.classList.add('flex');
    
    setTimeout(() => {
        conteudo.classList.remove('scale-95');
        conteudo.classList.add('scale-100');
    }, 10);
}

function fecharModal() {
    const modal = document.getElementById('modal_resultado');
    const conteudo = document.getElementById('modal_conteudo_interno');
    
    conteudo.classList.remove('scale-100');
    conteudo.classList.add('scale-95');
    
    setTimeout(() => {
        // A MÁGICA: Remove o flex e volta o hidden!
        modal.classList.remove('flex');
        modal.classList.add('hidden');
        
        const audioPlayer = document.querySelector('#modal_output_container audio');
        if (audioPlayer) audioPlayer.pause();
    }, 200);
}

function copiarTextoHist() {
    const texto = document.getElementById('texto_resgate').innerText;
    navigator.clipboard.writeText(texto).then(() => {
        alert("Conteúdo copiado para a área de transferência!");
    });
}

function baixarTxtHist(ferramenta, dataStr) {
    const texto = document.getElementById('texto_resgate').innerText;
    const blob = new Blob([texto], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `${ferramenta.replace(' ', '_')}_${dataStr.replace(/[\/:]/g, '-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function baixarSRTDireto(srt) {
    const blob = new Blob([srt], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `legenda_${new Date().getTime()}.srt`;
    link.click();
}

function encaminharPara(destino, index) {
    const reg = histDadosAtuais[index];
    const texto = reg.resultado;
    
    if (destino === 'script') {
        sessionStorage.setItem('script_ideia_base', texto);
        window.location.href = '/script-forge';
    } else if (destino === 'voice') {
        localStorage.setItem('texto_pendente_voice', texto);
        window.location.href = '/voice-synthesizer';
    } else if (destino === 'seo') {
        sessionStorage.setItem('seo_conteudo', texto);
        window.location.href = '/meta-seo';
    }
}
