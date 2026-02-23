// CONFIGURAÇÕES GLOBAIS
const URL_API_VOZES = "https://tts.zappclube.com.br/vozes";
const URL_API_DIRETA = "https://tts.zappclube.com.br/gerar_narracao"; 
let ideiasGlobais = []; 
let srtGlobal = ""; 
let vozSelecionada = "pt-BR-AntonioNeural"; 
let vozesData = [];
let arquivoVozMixer = null;
let arquivoBgMixer = null;

// INICIALIZAÇÃO
window.onload = async function() {
    mudarAba('aba_legends', document.getElementById('btn_menu_legends'));
    aplicarPresetMixer();
    configurarDragAndDropLegends();
    configurarDragAndDropMixer('dropzone_mixer_voz', 'arquivo_mixer_voz', 'nome_mixer_voz', 'icone_mixer_voz');
    configurarDragAndDropMixer('dropzone_mixer_bg', 'arquivo_mixer_bg', 'nome_mixer_bg', 'icone_mixer_bg');
    
    try {
        const resposta = await fetch(URL_API_VOZES);
        const dados = await resposta.json();
        if(dados.status === "erro") throw new Error(dados.mensagem);
        vozesData = dados.vozes;
        renderizarListaVozes();
    } catch (error) { console.log(error); }
};

// --- NAVEGAÇÃO ENTRE ABAS ---
function mudarAba(idAbaDestino, btnClicado) {
    document.querySelectorAll('.aba-conteudo').forEach(aba => { 
        aba.classList.add('aba-oculta'); 
        aba.classList.remove('block'); 
    });
    const abaDestino = document.getElementById(idAbaDestino);
    if(abaDestino){
        abaDestino.classList.remove('aba-oculta'); 
        abaDestino.classList.add('block');
    }
    
    document.querySelectorAll('.menu-btn').forEach(btn => {
        btn.className = "menu-btn w-full flex items-center gap-3 px-3 py-2.5 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-lg transition-all text-left text-sm border border-transparent";
        btn.querySelector('i').className = btn.querySelector('i').className.replace(/text-purple-400|drop-shadow|text-cyan-400|text-amber-400|text-orange-400|text-pink-400|text-indigo-400|text-yellow-400|text-blue-400/g, '').trim();
    });
    
    if(btnClicado) {
        let shadowClass = 'shadow-[0_0_15px_rgba(255,255,255,0.05)]';
        btnClicado.className = `menu-btn w-full flex items-center gap-3 px-3 py-2.5 text-white bg-zinc-800/80 rounded-lg ${shadowClass} border border-zinc-700/50 text-left text-sm relative z-10 overflow-hidden`;
    }
}

// --- FUNÇÕES DE UTILIDADE (CONTADORES E SLIDERS) ---
function contarPalavras(textAreaId, contadorId) {
    const texto = document.getElementById(textAreaId).value.trim();
    const palavras = texto === "" ? 0 : texto.split(/\s+/).length;
    document.getElementById(contadorId).innerText = `${palavras} palavras`;
}

function ajustarSliderMixer(sliderId, direction, lblId) {
    const slider = document.getElementById(sliderId);
    let step = parseFloat(slider.step);
    let val = parseFloat(slider.value);
    let newVal = val + (direction * step);
    if (newVal > parseFloat(slider.max)) newVal = parseFloat(slider.max);
    if (newVal < parseFloat(slider.min)) newVal = parseFloat(slider.min);
    slider.value = newVal;
    document.getElementById(lblId).innerText = (step % 1 !== 0) ? newVal.toFixed(1) : Math.round(newVal);
}

// --- INTEGRAÇÃO COM N8N (WEBHOOKS) ---
async function chamarParaphraser() {
    const btn = document.getElementById('btn_gerar_paraphraser');
    const btnTexto = document.getElementById('txt_btn_transmutar');
    const idioma = document.getElementById('paraphraser_idioma').value;
    let conteudo = document.getElementById('paraphraser_conteudo').value;

    if(!conteudo.trim()) return alert("Por favor, cole um texto.");

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    btnTexto.innerText = "Transmutando...";
    
    try {
        const res = await fetch("https://n8n.zappclube.com.br/webhook-test/gerador-paraphraser", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto: conteudo, idioma: idioma })
        });
        const dados = await res.json();
        document.getElementById('paraphraser_resultado').value = dados.texto_transmutado;
        contarPalavras('paraphraser_resultado', 'contador_palavras_out');
    } catch (error) {
        alert("Erro no Paraphraser: " + error.message);
    } finally {
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        btnTexto.innerText = "Transmutar (1 coin)";
    }
}

// ... (Restante das funções: chamarMineracao, chamarGeradorIdeias, gerarAudioCompleto, etc.)
// Diretor, o JS é longo. Mantenha as funções originais do seu <script> aqui dentro.
