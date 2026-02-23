// ==========================================
// CONFIGURAÇÕES GLOBAIS
// ==========================================
const URL_API_VOZES = "https://tts.zappclube.com.br/vozes";
const URL_API_DIRETA = "https://tts.zappclube.com.br/gerar_narracao"; 
let ideiasGlobais = []; 
let srtGlobal = ""; 
let vozSelecionada = "pt-BR-AntonioNeural"; 
let vozesData = [];
let arquivoVozMixer = null;
let arquivoBgMixer = null;

// ==========================================
// INICIALIZAÇÃO E BLINDAGEM DE CARREGAMENTO
// ==========================================
window.onload = async function() {
    // Proteções de Segurança: Só executa se os elementos existirem na página atual
    const btnLegends = document.getElementById('btn_menu_legends');
    if(btnLegends && document.getElementById('aba_legends')) {
        mudarAba('aba_legends', btnLegends);
    }
    
    if(document.getElementById('mixer_preset')) aplicarPresetMixer();
    if(document.getElementById('dropzone_legends')) configurarDragAndDropLegends();
    if(document.getElementById('dropzone_mixer_voz')) configurarDragAndDropMixer('dropzone_mixer_voz', 'arquivo_mixer_voz', 'nome_mixer_voz', 'icone_mixer_voz');
    if(document.getElementById('dropzone_mixer_bg')) configurarDragAndDropMixer('dropzone_mixer_bg', 'arquivo_mixer_bg', 'nome_mixer_bg', 'icone_mixer_bg');
    
    if(document.getElementById('lista_vozes')) {
        try {
            const resposta = await fetch(URL_API_VOZES);
            const dados = await resposta.json();
            if(dados.status === "erro") throw new Error(dados.mensagem);
            vozesData = dados.vozes;
            renderizarListaVozes();
        } catch (error) { 
            console.log("Aviso: Falha ao carregar vozes.", error); 
        }
    }

    // Configura Drag and Drop do Paraphraser (se existir na tela)
    const dropzoneParaphraser = document.getElementById('dropzone_paraphraser');
    const fileInputParaphraser = document.getElementById('arquivo_txt_paraphraser');
    if(dropzoneParaphraser && fileInputParaphraser) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => dropzoneParaphraser.addEventListener(ev, preventDefaults, false));
        function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
        
        ['dragenter', 'dragover'].forEach(ev => {
            dropzoneParaphraser.addEventListener(ev, () => {
                dropzoneParaphraser.classList.add('border-pink-400', 'bg-pink-500/10', 'scale-[1.02]');
                dropzoneParaphraser.querySelector('i').classList.add('text-pink-400', '-translate-y-1');
            }, false);
        });
        
        ['dragleave', 'drop'].forEach(ev => {
            dropzoneParaphraser.addEventListener(ev, () => {
                dropzoneParaphraser.classList.remove('border-pink-400', 'bg-pink-500/10', 'scale-[1.02]');
                dropzoneParaphraser.querySelector('i').classList.remove('text-pink-400', '-translate-y-1');
            }, false);
        });
        
        dropzoneParaphraser.addEventListener('drop', (e) => {
            let files = e.dataTransfer.files;
            if(files.length > 0 && files[0].name.endsWith('.txt')) { 
                fileInputParaphraser.files = files; 
                lerArquivoTXTParaphraser({target: fileInputParaphraser}); 
            } else { alert("Por favor, solte apenas arquivos .txt"); }
        }, false);
    }
};

// ==========================================
// FUNÇÕES DE UTILIDADE E UI
// ==========================================
function mudarAba(idAbaDestino, btnClicado) {
    document.querySelectorAll('.aba-conteudo').forEach(aba => { 
        aba.classList.add('aba-oculta'); 
        aba.classList.remove('block'); 
    });
    
    const abaDestino = document.getElementById(idAbaDestino);
    if(abaDestino) {
        abaDestino.classList.remove('aba-oculta'); 
        abaDestino.classList.add('block');
    }
    
    document.querySelectorAll('.menu-btn').forEach(btn => {
        btn.className = "menu-btn w-full flex items-center gap-3 px-3 py-2.5 text-zinc-400 hover:text-white hover:bg-zinc-800/50 rounded-lg transition-all text-left text-sm border border-transparent";
        btn.querySelector('i').className = btn.querySelector('i').className.replace(/text-purple-400|drop-shadow-\[0_0_5px_rgba\(168,85,247,0\.8\)\]|text-cyan-400|drop-shadow-\[0_0_5px_rgba\(34,211,238,0\.8\)\]|text-amber-400|drop-shadow-\[0_0_5px_rgba\(245,158,11,0\.8\)\]|text-orange-400|drop-shadow-\[0_0_5px_rgba\(249,115,22,0\.8\)\]|text-pink-400|drop-shadow-\[0_0_5px_rgba\(236,72,153,0\.8\)\]|text-indigo-400|drop-shadow-\[0_0_5px_rgba\(99,102,241,0\.8\)\]|text-yellow-400|drop-shadow-\[0_0_5px_rgba\(250,204,21,0\.8\)\]|text-blue-400|drop-shadow-\[0_0_5px_rgba\(96,165,250,0\.8\)\]/g, '').trim();
    });
    
    if(btnClicado) {
        let colorClass = 'text-zinc-400';
        let shadowClass = '';
        let borderClass = 'border-transparent';
        
        if(idAbaDestino === 'aba_ideias') { colorClass = 'text-yellow-400 drop-shadow-[0_0_5px_rgba(250,204,21,0.8)]'; borderClass = 'border-yellow-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(250,204,21,0.1)]'; }
        if(idAbaDestino === 'aba_minerador') { colorClass = 'text-indigo-400 drop-shadow-[0_0_5px_rgba(99,102,241,0.8)]'; borderClass = 'border-indigo-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(99,102,241,0.1)]'; }
        if(idAbaDestino === 'aba_reescritor') { colorClass = 'text-pink-400 drop-shadow-[0_0_5px_rgba(236,72,153,0.8)]'; borderClass = 'border-pink-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(236,72,153,0.1)]'; }
        if(idAbaDestino === 'aba_script') { colorClass = 'text-orange-400 drop-shadow-[0_0_5px_rgba(249,115,22,0.8)]'; borderClass = 'border-orange-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(249,115,22,0.1)]'; }
        if(idAbaDestino === 'aba_voice') { colorClass = 'text-purple-400 drop-shadow-[0_0_5px_rgba(168,85,247,0.8)]'; borderClass = 'border-purple-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(168,85,247,0.1)]'; }
        if(idAbaDestino === 'aba_mixer') { colorClass = 'text-amber-400 drop-shadow-[0_0_5px_rgba(245,158,11,0.8)]'; borderClass = 'border-amber-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(245,158,11,0.1)]'; }
        if(idAbaDestino === 'aba_seo') { colorClass = 'text-blue-400 drop-shadow-[0_0_5px_rgba(96,165,250,0.8)]'; borderClass = 'border-blue-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(96,165,250,0.1)]'; }
        if(idAbaDestino === 'aba_thumb') { colorClass = 'text-pink-400 drop-shadow-[0_0_5px_rgba(236,72,153,0.8)]'; borderClass = 'border-pink-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(236,72,153,0.1)]'; }
        if(idAbaDestino === 'aba_legends') { colorClass = 'text-cyan-400 drop-shadow-[0_0_5px_rgba(34,211,238,0.8)]'; borderClass = 'border-cyan-500/20'; shadowClass = 'shadow-[0_0_15px_rgba(34,211,238,0.1)]'; }
        
        btnClicado.className = `menu-btn w-full flex items-center gap-3 px-3 py-2.5 text-white bg-zinc-800/80 rounded-lg ${shadowClass} border ${borderClass} text-left text-sm relative z-10 overflow-hidden`;
        btnClicado.querySelector('i').className += ' ' + colorClass;
    }
}

function contarPalavras(textAreaId, contadorId) {
    const textArea = document.getElementById(textAreaId);
    if(!textArea) return;
    const texto = textArea.value.trim();
    const palavras = texto === "" ? 0 : texto.split(/\s+/).length;
    const contador = document.getElementById(contadorId);
    if(contador) contador.innerText = `${palavras} palavras`;
}

function copiarResultadoParaphraser() {
    const texto = document.getElementById('paraphraser_resultado').value;
    if(!texto) return;
    navigator.clipboard.writeText(texto).then(() => { alert("Texto copiado com sucesso!"); });
}

function copiarTexto(base64Str, btnElement) {
    const texto = decodeURIComponent(escape(atob(base64Str)));
    navigator.clipboard.writeText(texto).then(() => {
        const originalText = btnElement.innerHTML;
        btnElement.innerHTML = `<i class="fa-solid fa-check"></i> Copiado!`;
        btnElement.classList.replace('text-pink-500', 'text-emerald-400');
        setTimeout(() => {
            btnElement.innerHTML = originalText;
            btnElement.classList.replace('text-emerald-400', 'text-pink-500');
        }, 2000);
    });
}

function lerArquivoTXTParaphraser(event) {
    const arquivo = event.target.files[0];
    if (!arquivo) return;
    
    document.getElementById('nome_arquivo_txt').innerText = arquivo.name;
    document.getElementById('icone_upload_txt').className = "fa-solid fa-file-circle-check text-3xl text-pink-400 mb-2 drop-shadow-md";

    const leitor = new FileReader();
    leitor.onload = function(e) { 
        const textarea = document.getElementById('paraphraser_conteudo');
        textarea.value = e.target.result; 
        contarPalavras('paraphraser_conteudo', 'contador_palavras_in');
    };
    leitor.readAsText(arquivo);
}

// ==========================================
// ROTEADORES DE FLUXO (ENVIAR DE UMA FERRAMENTA PARA OUTRA)
// ==========================================
function enviarMinerParaParaphraser(btnElement) {
    const card = btnElement.closest('.miner-card');
    const titulo = card.querySelector('h4').innerText;
    const texto = card.querySelector('.miner-texto').innerText;
    document.getElementById('paraphraser_conteudo').value = `TÍTULO ORIGINAL: ${titulo}\n\n${texto}`;
    contarPalavras('paraphraser_conteudo', 'contador_palavras_in');
    document.getElementById('btn_menu_reescritor').click();
}

function enviarLegendsParaParaphraser() {
    const texto = document.getElementById('legends_txt_resultado').value;
    if(!texto || texto.trim() === "") return alert("Transcreva um áudio primeiro!");
    document.getElementById('paraphraser_conteudo').value = texto;
    contarPalavras('paraphraser_conteudo', 'contador_palavras_in');
    document.getElementById('btn_menu_reescritor').click();
}

function enviarParaScriptForge(index) {
    const ideia = ideiasGlobais[index];
    const textoMontado = `TÍTULO: ${ideia.titulo}\nGANCHO: ${ideia.gancho}\nRESUMO: ${ideia.resumo}`;
    document.getElementById('script_ideia_base').value = textoMontado;
    contarPalavras('script_ideia_base', 'contador_script_in');
    document.getElementById('btn_menu_script').click(); 
}

function enviarScriptParaVoice() {
    const roteiroPronto = document.getElementById('script_final_editavel').value;
    if(!roteiroPronto || roteiroPronto.trim() === "") return alert("Aviso: O roteiro está vazio!"); 
    document.getElementById('texto_voz').value = roteiroPronto;
    document.getElementById('btn_menu_voice').click(); 
}

function enviarParaphraserParaVoice() {
    const textoPronto = document.getElementById('paraphraser_resultado').value;
    if(!textoPronto || textoPronto.trim() === "") return alert("Aviso: O texto está vazio!"); 
    document.getElementById('texto_voz').value = textoPronto;
    document.getElementById('btn_menu_voice').click(); 
}

// ==========================================
// 🚀 NOVAS CHAMADAS FASTAPI (NATIVAS)
// ==========================================

// 1. GEN INSIGHTS (GROQ/LLAMA 3)
async function chamarGeradorIdeias() {
    const btn = document.getElementById('btn_gerar_ideias');
    const container = document.getElementById('container_ideias');
    const tema = document.getElementById('ideia_tema')?.value;
    const publico = document.getElementById('ideia_publico')?.value || "Geral";
    const tom = document.getElementById('ideia_tom')?.value;

    if(!tema) return alert("Por favor, preencha o Nicho ou Tema."); 

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    container.innerHTML = `<div class="flex flex-col items-center justify-center py-10 w-full h-full relative z-10"><i class="fa-solid fa-brain fa-fade text-4xl text-yellow-500 mb-4"></i><p class="text-zinc-400 text-sm animate-pulse">A IA Groq está analisando tendências e elaborando roteiros magnéticos...</p></div>`;

    try {
        const res = await fetch("/api/v1/gen-insights", { 
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }, 
            body: JSON.stringify({ tema, publico, tom }) 
        });
        
        if(!res.ok) {
            let erroReal = "Erro desconhecido do servidor.";
            try { const dadosErro = await res.json(); erroReal = dadosErro.detail || erroReal; } catch(e) {}
            throw new Error(erroReal);
        }

        const dadosLimpos = await res.json();
        
        ideiasGlobais = dadosLimpos.ideias; 
        container.innerHTML = '<div class="w-full text-left space-y-4 relative z-10" id="lista_ideias_geradas"></div>';
        const listaDiv = document.getElementById('lista_ideias_geradas');

        ideiasGlobais.forEach((ideia, index) => {
            listaDiv.innerHTML += `
                <div class="bg-[#121214] border border-yellow-500/30 rounded-xl p-5 hover:border-yellow-500/60 transition-colors shadow-inner">
                    <div class="flex items-center justify-between mb-3 border-b border-zinc-800 pb-2">
                        <span class="bg-yellow-500/20 text-yellow-400 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider">Ideia ${index + 1}</span>
                        <button onclick="enviarParaScriptForge(${index})" class="text-orange-400 hover:text-white transition-colors text-xs font-bold uppercase tracking-wider flex items-center gap-2 bg-orange-500/10 px-3 py-1.5 rounded-lg border border-orange-500/20 hover:bg-orange-600"><i class="fa-solid fa-fire"></i> Script Forge</button>
                    </div>
                    <h3 class="text-white font-bold text-lg mb-2 group-hover:text-yellow-300 transition-colors">${ideia.titulo}</h3>
                    <p class="text-sm text-zinc-300 mb-2 border-l-2 border-yellow-500/50 pl-3"><strong class="text-yellow-500/80">Gancho:</strong> ${ideia.gancho}</p>
                    <p class="text-sm text-zinc-400 leading-relaxed"><strong class="text-yellow-500/80">Visão Geral:</strong> ${ideia.resumo}</p>
                </div>`;
        });
    } catch (error) { 
        container.innerHTML = `<p class="text-red-400 font-bold p-5 relative z-10"><i class="fa-solid fa-triangle-exclamation"></i> Erro Técnico: ${error.message}</p>`; 
    } finally { 
        btn.classList.remove('opacity-70', 'cursor-not-allowed'); 
    }
}

// 2. PARAPHRASER (GEMINI 2.5 FLASH)
async function chamarParaphraser() {
    const btn = document.getElementById('btn_gerar_paraphraser');
    const btnTexto = document.getElementById('txt_btn_transmutar');
    const conteudo = document.getElementById('paraphraser_conteudo').value;
    const modo = document.getElementById('paraphraser_modo').value;
    const canal = document.getElementById('paraphraser_canal').value || "Canal Genérico";

    if(!conteudo.trim()) return alert("Por favor, cole um texto ou suba um arquivo .TXT.");

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    btnTexto.innerHTML = `Transmutando... <i class="fa-solid fa-circle-notch fa-spin ml-1"></i>`;
    document.getElementById('paraphraser_resultado').value = "Os motores neurais do Google estão reescrevendo seu texto. Aguarde...";

    try {
        const res = await fetch("/api/v1/paraphraser", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ texto: conteudo, modo: modo, canal: canal })
        });
        
        if(!res.ok) {
            let erroReal = "Erro desconhecido do servidor.";
            try { const dadosErro = await res.json(); erroReal = dadosErro.detail || erroReal; } catch(e) {}
            throw new Error(erroReal);
        }
        
        const dados = await res.json();
        document.getElementById('paraphraser_resultado').value = dados.texto_transmutado;
        contarPalavras('paraphraser_resultado', 'contador_palavras_out');

    } catch (error) {
        document.getElementById('paraphraser_resultado').value = "Erro Técnico: " + error.message;
    } finally {
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        btnTexto.innerText = "Transmutar Texto";
    }
}

// ==========================================
// CHAMADAS ANTIGAS (AINDAS NO N8N - MIGRAR EM BREVE)
// ==========================================
async function chamarScriptForge() {
    const btn = document.getElementById('btn_gerar_script');
    const ideiaBase = document.getElementById('script_ideia_base').value;
    const canal = document.getElementById('script_canal').value || "Canal Não Informado";
    const formato = document.getElementById('script_formato').value;
    const tamanho = document.getElementById('script_tamanho').value || "Duração livre";
    const instrucoes = document.getElementById('script_instrucoes').value || "Nenhuma instrução extra.";
    const tom = document.getElementById('ideia_tom') ? document.getElementById('ideia_tom').value : "Sombrio e Misterioso"; 

    if(!ideiaBase.trim()) return alert("Você precisa de uma Ideia Base para gerar um roteiro."); 

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    document.getElementById('script_final_editavel').value = "Nossos motores de inteligência artificial estão forjando o seu roteiro otimizado. Isso pode levar alguns segundos...\n\nAguarde o processamento neural...";

    const WEBHOOK_SCRIPT = "https://n8n.zappclube.com.br/webhook-test/gerador-script";

    try {
        const res = await fetch(WEBHOOK_SCRIPT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ideia_base: ideiaBase, canal: canal, formato: formato, tamanho: tamanho, tom: tom, instrucoes: instrucoes })
        });
        const dadosN8N = await res.json();
        document.getElementById('script_final_editavel').value = dadosN8N.roteiro;
        contarPalavras('script_final_editavel', 'contador_script_out');
    } catch (error) { document.getElementById('script_final_editavel').value = "Erro na conexão com os motores neurais: " + error.message; } 
    finally { btn.classList.remove('opacity-70', 'cursor-not-allowed'); }
}

async function chamarMetaSEO() {
    const btn = document.getElementById('btn_gerar_seo');
    const conteudo = document.getElementById('seo_conteudo').value;
    const keyword = document.getElementById('seo_keyword').value || "Geral";
    const canal = document.getElementById('seo_canal').value || "Meu Canal";

    if(!conteudo.trim()) return alert("Por favor, cole um Roteiro ou suba o arquivo .SRT para que a IA possa analisar.");

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    document.getElementById('seo_resultado').value = "A IA está lendo a história e arquitetando o SEO perfeito para o Algoritmo...\n\nAguarde...";

    const WEBHOOK_SEO = "https://n8n.zappclube.com.br/webhook-test/gerador-seo";

    try {
        const res = await fetch(WEBHOOK_SEO, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ conteudo: conteudo, keyword: keyword, canal: canal })
        });
        const dadosN8N = await res.json();
        document.getElementById('seo_resultado').value = dadosN8N.seo_result;
    } catch (error) { document.getElementById('seo_resultado').value = "Erro na conexão com os motores neurais: " + error.message; } 
    finally { btn.classList.remove('opacity-70', 'cursor-not-allowed'); }
}

async function chamarThumbMaker() {
    const btn = document.getElementById('btn_gerar_thumb');
    const txtBtn = document.getElementById('txt_btn_thumb');
    const container = document.getElementById('container_thumbs');
    
    const titulo = document.getElementById('thumb_titulo').value;
    const roteiro = document.getElementById('thumb_roteiro').value;
    const estilo = document.getElementById('thumb_estilo').value;
    const texto_arte = document.getElementById('thumb_texto_arte').value || "SEM TEXTO";

    if(!titulo.trim() || !roteiro.trim()) return alert("Por favor, preencha o Título e cole o Roteiro para o Diretor de Arte ler.");

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    txtBtn.innerHTML = `Lendo Roteiro e Criando Arte... <i class="fa-solid fa-circle-notch fa-spin ml-1"></i>`;
    
    container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-full text-center py-20 loader-pulse">
            <div class="flex gap-2 mb-4">
                <div class="w-4 h-4 bg-pink-500 rounded-full"></div>
                <div class="w-4 h-4 bg-pink-500 rounded-full"></div>
                <div class="w-4 h-4 bg-pink-500 rounded-full"></div>
            </div>
            <h3 class="text-sm font-bold text-pink-400">O Diretor de Arte está analisando a história...</h3>
        </div>
    `;

    const WEBHOOK_THUMB = "https://n8n.zappclube.com.br/webhook-test/gerador-thumb";

    try {
        const res = await fetch(WEBHOOK_THUMB, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ titulo: titulo, roteiro: roteiro, estilo: estilo, texto_arte: texto_arte })
        });
        
        const dadosStr = await res.json();
        let dados = typeof dadosStr === 'string' ? JSON.parse(dadosStr.replace(/```json/g, '').replace(/```/g, '').trim()) : dadosStr;

        container.innerHTML = ''; 

        if(dados.conflito_principal) {
            container.innerHTML += `
                <div class="mb-5 p-4 bg-[#121214] rounded-lg border border-pink-500/30 shadow-inner">
                    <h3 class="text-xs font-bold text-pink-400 mb-2 uppercase tracking-wider flex items-center gap-2"><i class="fa-solid fa-crosshairs"></i> Conflito Principal (Âncora)</h3>
                    <p class="text-sm text-zinc-300 italic">"${dados.conflito_principal}"</p>
                </div>
            `;
        }

        if(dados.capas && Array.isArray(dados.capas)) {
            dados.capas.forEach((capa, index) => {
                container.innerHTML += `
                    <div class="bg-[#121214] border border-zinc-800/80 rounded-xl p-5 hover:border-pink-500/50 transition-colors mb-4 shadow-inner">
                        <div class="flex items-center justify-between mb-3 border-b border-zinc-800 pb-2">
                            <span class="bg-pink-500/20 text-pink-400 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider">Ideia ${index + 1}: ${capa.estrategia}</span>
                        </div>
                        
                        <p class="text-xs text-zinc-400 mb-4 leading-relaxed border-l-2 border-zinc-700 pl-3 italic">"${capa.psicologia}"</p>
                        
                        <div>
                            <div class="flex items-center justify-between mb-1">
                                <span class="block text-[10px] font-bold text-zinc-500 uppercase">Prompt Gringo (Midjourney/Flux):</span>
                                <button onclick="copiarTexto('${btoa(unescape(encodeURIComponent(capa.prompt_gringo)))}', this)" class="text-pink-500 hover:text-white transition-colors text-xs flex items-center gap-1"><i class="fa-solid fa-copy"></i> Copiar</button>
                            </div>
                            <textarea class="w-full bg-[#09090b] border border-zinc-700/80 rounded px-3 py-2 text-emerald-400/90 text-xs font-mono resize-none h-20 shadow-inner" readonly>${capa.prompt_gringo}</textarea>
                        </div>
                    </div>
                `;
            });
        } else {
            container.innerHTML += `<p class="text-zinc-400 text-center py-10">Nenhuma capa retornada pela IA.</p>`;
        }

    } catch (error) {
        container.innerHTML = `<p class="text-red-400 text-center py-10">Erro ao comunicar com a IA Visual: ${error.message}</p>`;
    } finally {
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        txtBtn.innerHTML = "Gerar Direção de Arte (5 coins)";
    }
}


// ==========================================
// AUDIO MIXER, MINER E GEN LEGENDS (NATIVOS ANTIGOS)
// ==========================================
function trocarFonteMiner() {
    const fonte = document.getElementById('miner_fonte').value;
    if (fonte === 'reddit') {
        document.getElementById('campos_reddit').classList.remove('hidden');
        document.getElementById('campos_geral').classList.add('hidden');
    } else {
        document.getElementById('campos_reddit').classList.add('hidden');
        document.getElementById('campos_geral').classList.remove('hidden');
        let placeholder = "Digite o que deseja buscar na rede...";
        let labelText = "Termo de Busca (Deep Web)";
        
        if(fonte === 'wiki') {
            placeholder = "Ex: Fatos assustadores, Dom Pedro I...";
            labelText = "Tópico (Wikipedia)";
        } else if(fonte === 'news') {
            placeholder = "Ex: Casos criminais, Descobertas científicas...";
            labelText = "Assunto (Google News)";
        }
        
        document.getElementById('miner_query_geral').placeholder = placeholder;
        document.getElementById('lbl_miner_query_geral').innerText = labelText;
        document.getElementById('box_traduzir_web').style.display = (fonte === 'wiki' || fonte === 'news') ? 'none' : 'flex';
    }
}

async function iniciarMineracao() {
    const btn = document.getElementById('btn_iniciar_miner');
    const txtBtn = document.getElementById('txt_btn_miner');
    const container = document.getElementById('miner_resultados_container');
    const fonte = document.getElementById('miner_fonte').value;

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    txtBtn.innerHTML = `Vascunhando a Web... <i class="fa-solid fa-circle-notch fa-spin ml-1"></i>`;
    container.innerHTML = `
        <div class="flex flex-col items-center justify-center h-full text-center py-20 loader-pulse">
            <div class="flex gap-2 mb-4">
                <div class="w-4 h-4 bg-indigo-500 rounded-full"></div>
                <div class="w-4 h-4 bg-indigo-500 rounded-full"></div>
                <div class="w-4 h-4 bg-indigo-500 rounded-full"></div>
            </div>
            <h3 class="text-sm font-bold text-indigo-400">Extraindo dados da nuvem...</h3>
            <p class="text-xs text-zinc-500 mt-2">Pode levar alguns segundos se a busca for profunda.</p>
        </div>
    `;

    let url = "https://tts.zappclube.com.br/miner/" + fonte;
    let payload = {};

    if (fonte === 'reddit') {
        payload = {
            sub: document.getElementById('miner_sub').value,
            query: document.getElementById('miner_query_reddit').value,
            min_words: parseInt(document.getElementById('miner_words').value) || 100,
            min_score: parseInt(document.getElementById('miner_score').value) || 10,
            sem_atualizacao: document.getElementById('miner_sem_atualizacao').checked
        };
    } else if (fonte === 'web') {
        payload = {
            query: document.getElementById('miner_query_geral').value,
            traduzir: document.getElementById('miner_traduzir_web').checked
        };
    } else if (fonte === 'wiki' || fonte === 'news') {
        payload = { query: document.getElementById('miner_query_geral').value };
    }

    try {
        const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const dados = await res.json();
        
        if (dados.status === "erro") throw new Error(dados.mensagem);
        if (!dados.data || dados.data.length === 0) throw new Error("Nenhum resultado profundo encontrado para essa busca.");

        container.innerHTML = ''; 

        dados.data.forEach((item, index) => {
            container.innerHTML += `
                <div class="miner-card bg-[#121214] border border-zinc-800/80 rounded-xl p-5 hover:border-indigo-500/50 transition-colors relative group shadow-inner mb-4">
                    <div class="flex justify-between items-start mb-3">
                        <span class="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 text-[10px] font-bold px-2 py-1 rounded uppercase tracking-wider flex items-center gap-1">
                            <i class="fa-solid fa-satellite-dish"></i> ${item.fonte}
                        </span>
                        <span class="text-xs text-zinc-500 font-bold"><i class="fa-solid fa-align-left mr-1"></i> ${item.palavras} palavras</span>
                    </div>
                    <h4 class="text-white font-bold text-lg mb-2 pr-4 leading-tight group-hover:text-indigo-300 transition-colors">${item.titulo}</h4>
                    <p class="miner-texto text-sm text-zinc-400 line-clamp-3 leading-relaxed mb-4">${item.texto}</p>
                    
                    <div class="flex items-center gap-3 border-t border-zinc-800/80 pt-4 relative z-10">
                        <button onclick="enviarMinerParaParaphraser(this)" class="flex-1 bg-pink-600 hover:bg-pink-500 text-white text-xs font-bold py-2.5 px-3 rounded-lg shadow-[0_0_10px_rgba(219,39,119,0.3)] transition-colors flex items-center justify-center gap-2 group-btn">
                            <i class="fa-solid fa-wand-magic-sparkles group-hover:rotate-12 transition-transform"></i> Transmutar
                        </button>
                        <button onclick="baixarTXT(this, '${item.titulo}')" class="bg-[#1a1a1e] hover:bg-zinc-700 text-zinc-300 text-xs font-bold py-2.5 px-4 rounded-lg border border-zinc-700 transition-colors flex items-center justify-center gap-2 group-btn">
                            <i class="fa-solid fa-download group-hover:-translate-y-0.5 transition-transform"></i> .TXT
                        </button>
                    </div>
                </div>
            `;
        });

    } catch (error) {
        container.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full text-center py-20 relative z-10">
                <i class="fa-solid fa-triangle-exclamation text-3xl text-red-500 mb-3 drop-shadow-[0_0_10px_rgba(239,68,68,0.5)]"></i>
                <h3 class="text-sm font-bold text-red-400">Erro na Mineração</h3>
                <p class="text-xs text-zinc-500 mt-1">${error.message}</p>
            </div>
        `;
    } finally {
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        txtBtn.innerHTML = "Iniciar Varredura";
    }
}

// ... [O restante do código do Audio Mixer, Legends e Downlodas continua idêntico] ...
function mostrarNomeMixer(event, idNome, idIcone) {
    const arquivo = event.target.files[0];
    if(arquivo) {
        document.getElementById(idNome).innerText = arquivo.name;
        document.getElementById(idIcone).className = "fa-solid fa-file-audio text-3xl text-amber-400 mb-2 drop-shadow-[0_0_8px_rgba(245,158,11,0.6)] animate-pulse";
        if(idNome === 'nome_mixer_voz') arquivoVozMixer = arquivo;
        if(idNome === 'nome_mixer_bg') arquivoBgMixer = arquivo;
    }
}

function aplicarPresetMixer() {
    const preset = document.getElementById('mixer_preset').value;
    if(preset === "manual") return;
    if(preset === "narrador_dark") {
        document.getElementById('mixer_vol_voz').value = 0; document.getElementById('lbl_mixer_vol_voz').innerText = "0";
        document.getElementById('mixer_vol_bg').value = -18; document.getElementById('lbl_mixer_vol_bg').innerText = "-18";
        document.getElementById('mixer_ducking').checked = true;
        document.getElementById('mixer_duck_amount').value = -14; document.getElementById('lbl_mixer_duck_amount').innerText = "-14";
        document.getElementById('mixer_eq_bass').value = 3; document.getElementById('lbl_eq_bass').innerText = "3";
        document.getElementById('mixer_eq_treble').value = 2; document.getElementById('lbl_eq_treble').innerText = "2";
        document.getElementById('mixer_compressor').checked = true;
        document.getElementById('mixer_comp_th').value = -18; document.getElementById('lbl_comp_th').innerText = "-18";
        document.getElementById('mixer_comp_ratio').value = 4; document.getElementById('lbl_comp_ratio').innerText = "4.0";
        document.getElementById('mixer_comp_makeup').value = 4; document.getElementById('lbl_comp_makeup').innerText = "4";
        document.getElementById('mixer_limiter_ceil').value = -1; document.getElementById('lbl_limiter_ceil').innerText = "-1.0";
    } else if(preset === "podcast") {
        document.getElementById('mixer_vol_voz').value = 0; document.getElementById('lbl_mixer_vol_voz').innerText = "0";
        document.getElementById('mixer_vol_bg').value = -24; document.getElementById('lbl_mixer_vol_bg').innerText = "-24";
        document.getElementById('mixer_ducking').checked = true;
        document.getElementById('mixer_duck_amount').value = -12; document.getElementById('lbl_mixer_duck_amount').innerText = "-12";
        document.getElementById('mixer_eq_bass').value = 1; document.getElementById('lbl_eq_bass').innerText = "1";
        document.getElementById('mixer_eq_treble').value = 1; document.getElementById('lbl_eq_treble').innerText = "1";
        document.getElementById('mixer_compressor').checked = true;
        document.getElementById('mixer_comp_th').value = -20; document.getElementById('lbl_comp_th').innerText = "-20";
        document.getElementById('mixer_comp_ratio').value = 3; document.getElementById('lbl_comp_ratio').innerText = "3.0";
        document.getElementById('mixer_comp_makeup').value = 2; document.getElementById('lbl_comp_makeup').innerText = "2";
        document.getElementById('mixer_limiter_ceil').value = -2; document.getElementById('lbl_limiter_ceil').innerText = "-2.0";
    }
}

function ajustarSliderMixer(sliderId, direction, lblId) {
    const slider = document.getElementById(sliderId);
    let step = parseFloat(slider.step);
    let val = parseFloat(slider.value);
    
    let newVal = val + (direction * step);
    let max = parseFloat(slider.max);
    let min = parseFloat(slider.min);
    
    if (newVal > max) newVal = max;
    if (newVal < min) newVal = min;
    
    if (step % 1 !== 0) {
        slider.value = newVal.toFixed(1);
        document.getElementById(lblId).innerText = newVal.toFixed(1);
    } else {
        slider.value = Math.round(newVal);
        document.getElementById(lblId).innerText = Math.round(newVal);
    }
}

function configurarDragAndDropLegends() {
    const dropzone = document.getElementById('dropzone_legends');
    const fileInput = document.getElementById('arquivo_audio_legends');
    if(!dropzone) return;
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => dropzone.addEventListener(ev, preventDefaults, false));
    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
    ['dragenter', 'dragover'].forEach(ev => {
        dropzone.addEventListener(ev, () => {
            dropzone.classList.add('border-cyan-400', 'bg-cyan-500/10', 'scale-[1.02]');
            dropzone.querySelector('i').classList.add('text-cyan-400', '-translate-y-2');
        }, false);
    });
    ['dragleave', 'drop'].forEach(ev => {
        dropzone.addEventListener(ev, () => {
            dropzone.classList.remove('border-cyan-400', 'bg-cyan-500/10', 'scale-[1.02]');
            dropzone.querySelector('i').classList.remove('text-cyan-400', '-translate-y-2');
        }, false);
    });
    dropzone.addEventListener('drop', (e) => {
        let files = e.dataTransfer.files;
        if(files.length > 0) { fileInput.files = files; mostrarNomeAudio({target: fileInput}); }
    }, false);
}

function configurarDragAndDropMixer(dropzoneId, inputId, labelId, iconId) {
    const dropzone = document.getElementById(dropzoneId);
    const fileInput = document.getElementById(inputId);
    if(!dropzone) return;
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(ev => dropzone.addEventListener(ev, preventDefaults, false));
    function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }
    ['dragenter', 'dragover'].forEach(ev => {
        dropzone.addEventListener(ev, () => {
            dropzone.classList.add('border-amber-400', 'bg-amber-500/10', 'shadow-[0_0_15px_rgba(245,158,11,0.2)]');
            dropzone.querySelector('i').classList.add('text-amber-400', '-translate-y-1');
        }, false);
    });
    ['dragleave', 'drop'].forEach(ev => {
        dropzone.addEventListener(ev, () => {
            dropzone.classList.remove('border-amber-400', 'bg-amber-500/10', 'shadow-[0_0_15px_rgba(245,158,11,0.2)]');
            dropzone.querySelector('i').classList.remove('text-amber-400', '-translate-y-1');
        }, false);
    });
    dropzone.addEventListener('drop', (e) => {
        let files = e.dataTransfer.files;
        if(files.length > 0) { fileInput.files = files; mostrarNomeMixer({target: fileInput}, labelId, iconId); }
    }, false);
}

async function chamarAudioMixer() {
    const btn = document.getElementById('btn_gerar_mixer');
    const txtBtn = document.getElementById('txt_btn_mixer');
    const container = document.getElementById('mixer_resultados_container');
    
    if(!arquivoVozMixer) return alert("Por favor, selecione o arquivo da Voz.");
    if(!arquivoBgMixer) return alert("Por favor, selecione o arquivo de Música de Fundo.");

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    txtBtn.innerHTML = `Mixando... <i class="fa-solid fa-circle-notch fa-spin ml-1"></i>`;
    
    container.classList.remove('hidden');
    container.innerHTML = `<div class="flex flex-col items-center justify-center py-5"><p class="text-sm font-bold text-amber-500 animate-pulse">O estúdio neural está processando o áudio...</p></div>`;

    const formData = new FormData();
    formData.append("voice_file", arquivoVozMixer);
    formData.append("bg_file", arquivoBgMixer);
    formData.append("voice_vol", document.getElementById('mixer_vol_voz').value);
    formData.append("bg_vol", document.getElementById('mixer_vol_bg').value);
    formData.append("ducking", document.getElementById('mixer_ducking').checked);
    formData.append("duck_amount", document.getElementById('mixer_duck_amount').value);
    formData.append("fade_in", document.getElementById('mixer_fade_in').value);
    formData.append("fade_out", document.getElementById('mixer_fade_out').value);
    formData.append("trim_silence", document.getElementById('mixer_trim').checked);
    formData.append("trim_pad", "80");
    formData.append("compressor", document.getElementById('mixer_compressor').checked);
    formData.append("comp_th", document.getElementById('mixer_comp_th').value);
    formData.append("comp_ratio", document.getElementById('mixer_comp_ratio').value);
    formData.append("comp_makeup", document.getElementById('mixer_comp_makeup').value);
    formData.append("limiter", "true");
    formData.append("limiter_ceil", document.getElementById('mixer_limiter_ceil').value);
    formData.append("eq_bass", document.getElementById('mixer_eq_bass').value);
    formData.append("eq_treble", document.getElementById('mixer_eq_treble').value);

    try {
        const res = await fetch("https://tts.zappclube.com.br/audio_mixer", { method: 'POST', body: formData });
        const dados = await res.json();
        if (dados.status === "erro") throw new Error(dados.mensagem);

        container.innerHTML = `
            <div class="flex flex-col items-center w-full">
                <div class="flex items-center gap-2 mb-4"><i class="fa-solid fa-circle-check text-xl text-amber-500 drop-shadow-[0_0_8px_rgba(245,158,11,0.8)]"></i><p class="text-sm font-bold text-amber-500">Masterização Concluída!</p></div>
                <audio id="player_mixer_final" controls class="w-full h-12 outline-none mb-4 bg-zinc-900 rounded-lg shadow-inner"></audio>
                <button onclick="baixarAudioMixado('${dados.audio_base64}')" class="w-full bg-[#121214] hover:bg-amber-600 text-amber-500 hover:text-white font-bold py-3 px-4 rounded-lg border border-amber-500/30 transition-colors flex items-center justify-center gap-2 shadow-[0_0_10px_rgba(245,158,11,0.1)] group relative z-10">
                    <i class="fa-solid fa-download group-hover:scale-110 transition-transform"></i> Baixar Áudio Final (.WAV)
                </button>
            </div>
        `;
        document.getElementById('player_mixer_final').src = "data:audio/wav;base64," + dados.audio_base64;

    } catch (error) {
        container.innerHTML = `<p class="text-red-400 text-sm p-3 font-bold"><i class="fa-solid fa-triangle-exclamation"></i> Erro do Servidor: ${error.message}</p>`;
    } finally {
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        txtBtn.innerHTML = "Iniciar Masterização (10 coins)";
    }
}

function baixarAudioMixado(base64) {
    const link = document.createElement('a');
    link.href = "data:audio/wav;base64," + base64;
    link.download = `Audio_Masterizado_DarkCreator_${new Date().getTime()}.wav`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function baixarTXT(btnElement, titulo) {
    const card = btnElement.closest('.miner-card');
    const texto = card.querySelector('.miner-texto').innerText;
    const blob = new Blob([texto], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Miner_${titulo.substring(0, 20).replace(/[^a-zA-Z0-9]/g, '_')}_${new Date().getTime()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function baixarTXTLegends() {
    const texto = document.getElementById('legends_txt_resultado').value;
    if(!texto || texto.trim() === "") return alert("Transcreva um áudio primeiro!");
    const blob = new Blob([texto], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Transcricao_Bruta_${new Date().getTime()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function baixarSRTLegends() {
    const srt = document.getElementById('legends_srt_resultado').value;
    if(!srt || srt.trim() === "") return alert("Transcreva um áudio primeiro!");
    const blob = new Blob([srt], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Legenda_Whisper_${new Date().getTime()}.srt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function baixarTXTSEO() {
    const textoSeo = document.getElementById('seo_resultado').value;
    if(!textoSeo || textoSeo.trim() === "") return alert("Gere o SEO primeiro antes de baixar!"); 
    const blob = new Blob([textoSeo], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `SEO_Otimizado_${new Date().getTime()}.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function baixarSRT() {
    if(!srtGlobal) return alert("Nenhuma legenda disponível para download.");
    const blob = new Blob([srtGlobal], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Legenda_DarkCreator_${new Date().getTime()}.srt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function mostrarNomeAudio(event) {
    const arquivo = event.target.files[0];
    if(arquivo) {
        document.getElementById('nome_arquivo_legends').innerText = arquivo.name;
        document.getElementById('icone_upload_legends').className = "fa-solid fa-file-circle-check text-4xl text-cyan-400 mb-3 drop-shadow-[0_0_8px_rgba(34,211,238,0.6)] animate-pulse";
    }
}

async function chamarGenLegends() {
    const btn = document.getElementById('btn_gerar_legends');
    const txtBtn = document.getElementById('txt_btn_legends');
    const arquivoInput = document.getElementById('arquivo_audio_legends');
    const idioma = document.getElementById('legends_idioma').value;
    const modelo = document.getElementById('legends_modelo').value;
    const txtOut = document.getElementById('legends_txt_resultado');
    const srtOut = document.getElementById('legends_srt_resultado');

    if (!arquivoInput.files || arquivoInput.files.length === 0) {
        return alert("Por favor, selecione ou arraste um arquivo de áudio/vídeo primeiro.");
    }

    const arquivo = arquivoInput.files[0];

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    txtBtn.innerHTML = `Transcrevendo na Nuvem... <i class="fa-solid fa-circle-notch fa-spin ml-1"></i>`;
    txtOut.value = "A IA Whisper está escutando o seu áudio e processando as legendas. Isso pode levar alguns segundos dependendo do tamanho do arquivo...";
    srtOut.value = "Aguardando sincronização de tempo...";

    const formData = new FormData();
    formData.append("file", arquivo);
    formData.append("language", idioma);
    formData.append("model_size", modelo);

    try {
        const res = await fetch("https://tts.zappclube.com.br/gen_legends", {
            method: 'POST',
            body: formData
        });
        const dados = await res.json();

        if (dados.status === "erro") {
            throw new Error(dados.mensagem);
        }

        txtOut.value = dados.txt;
        srtOut.value = dados.srt;
        srtGlobal = dados.srt; 

    } catch (error) {
        txtOut.value = "Erro de comunicação com o servidor neural: " + error.message;
        srtOut.value = "Falha no processamento.";
    } finally {
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        txtBtn.innerHTML = "Transcrever Áudio (20 coins)";
    }
}

function ajustarVelocidade(delta) {
    const slider = document.getElementById('velocidade');
    let newVal = parseFloat(slider.value) + delta;
    if(newVal > 2.0) newVal = 2.0;
    if(newVal < 0.5) newVal = 0.5;
    slider.value = newVal;
    document.getElementById('val_v').innerText = newVal.toFixed(1) + 'x';
}

function ajustarPitch(delta) {
    const slider = document.getElementById('pitch');
    let newVal = parseInt(slider.value) + delta;
    if(newVal > 50) newVal = 50;
    if(newVal < -50) newVal = -50;
    slider.value = newVal;
    document.getElementById('val_p').innerText = newVal + 'Hz';
}

function renderizarListaVozes() {
    const container = document.getElementById('lista_vozes');
    if(!container) return;
    container.innerHTML = '';
    vozesData.forEach(v => {
        let parts = v.shortName.split('-'); 
        let locale = parts[0] + '-' + parts[1]; 
        let actorName = parts[2].replace('Neural', ''); 
        let nomeLimpo = `${actorName} (${locale})`;

        let generoReal = "Neutro";
        if(v.gender === "Male") generoReal = "Masculino";
        if(v.gender === "Female") generoReal = "Feminino";

        let badgeClass = "bg-purple-500/10 text-purple-400 border border-purple-500/20"; 
        let iconUser = '<i class="fa-solid fa-robot text-purple-400"></i>';
        if(generoReal === "Masculino") { badgeClass = "bg-blue-500/10 text-blue-400 border border-blue-500/20"; iconUser = '<i class="fa-solid fa-user-tie text-blue-400"></i>'; }
        if(generoReal === "Feminino") { badgeClass = "bg-pink-500/10 text-pink-400 border border-pink-500/20"; iconUser = '<i class="fa-solid fa-user text-pink-400"></i>'; }
        
        let cardClass = v.shortName === vozSelecionada ? "border-emerald-500 bg-emerald-500/5 shadow-[0_0_15px_rgba(16,185,129,0.15)]" : "border-zinc-800 bg-[#09090b] hover:border-purple-500/50 hover:bg-purple-500/5 shadow-inner";

        container.innerHTML += `
            <div class="flex items-center justify-between p-3 rounded-xl border ${cardClass} cursor-pointer transition-all group relative z-10" onclick="selecionarVoz('${v.shortName}')">
                <div class="flex items-center gap-3"><div class="w-10 h-10 rounded-full bg-[#121214] flex items-center justify-center border border-zinc-700/50 shadow-inner group-hover:scale-110 transition-transform">${iconUser}</div>
                    <div><p class="text-sm font-bold text-white group-hover:text-purple-300 transition-colors">${nomeLimpo}</p><span class="text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${badgeClass} inline-block mt-0.5">${generoReal}</span></div>
                </div>
                <button class="w-9 h-9 rounded-full bg-[#121214] border border-zinc-700/50 flex items-center justify-center text-zinc-400 group-hover:bg-emerald-500 group-hover:text-white group-hover:border-emerald-400 group-hover:shadow-[0_0_10px_rgba(16,185,129,0.5)] transition-all hover:scale-110" onclick="tocarPreview(event, '${v.shortName}', '${actorName}')">
                    <i id="play_icon_${v.shortName}" class="fa-solid fa-play text-xs ml-0.5"></i>
                </button>
            </div>`;
    });
}

function selecionarVoz(shortName) { vozSelecionada = shortName; renderizarListaVozes(); }

async function tocarPreview(event, shortName, actorName) {
    event.stopPropagation(); 
    document.getElementById('player_preview').pause();
    const icon = document.getElementById(`play_icon_${shortName}`); 
    icon.className = "fa-solid fa-circle-notch fa-spin text-white"; 
    try {
        const res = await fetch(URL_API_DIRETA, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ texto: `Olá, eu sou a voz ${actorName}.`, voz: shortName, velocidade: 1.0, pitch: 0, volume: 0 }) });
        const dados = await res.json();
        if(dados.status === "erro") throw new Error(dados.mensagem);
        document.getElementById('player_preview').src = "data:audio/mp3;base64," + dados.audio_base64; 
        document.getElementById('player_preview').play();
        document.getElementById('player_preview').onended = () => { icon.className = "fa-solid fa-play text-xs ml-0.5"; };
    } catch (e) { icon.className = "fa-solid fa-play text-xs ml-0.5"; } 
}

async function gerarAudioCompleto() {
    const btn = document.getElementById('btn_gerar_voz');
    const textoVoz = document.getElementById('texto_voz').value;
    const containerPlayer = document.getElementById('player_container');
    
    if(!textoVoz.trim()) return alert("Digite um texto primeiro.");

    btn.classList.add('opacity-70', 'cursor-not-allowed');
    btn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin text-emerald-400"></i> <span>Gravando na Nuvem...</span>`;
    
    containerPlayer.classList.remove('hidden');
    containerPlayer.innerHTML = `
        <div class="flex flex-col items-center justify-center py-5">
            <div class="flex gap-2 mb-3">
                <div class="w-3 h-3 bg-emerald-500 rounded-full animate-bounce"></div>
                <div class="w-3 h-3 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                <div class="w-3 h-3 bg-emerald-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
            </div>
            <p class="text-sm font-bold text-emerald-400 animate-pulse">A IA está gravando a sua locução...</p>
        </div>
    `;

    const payload = { texto: textoVoz, voz: vozSelecionada, velocidade: parseFloat(document.getElementById('velocidade').value), pitch: parseInt(document.getElementById('pitch').value), volume: 0 };

    try {
        const resposta = await fetch(URL_API_DIRETA, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
        const dados = await resposta.json();
        
        if(dados.status === "erro") {
            containerPlayer.innerHTML = `<p class="text-red-400 text-sm p-3 font-bold"><i class="fa-solid fa-circle-xmark"></i> Erro do Servidor: ${dados.mensagem}</p>`;
            throw new Error(dados.mensagem);
        }

        if(dados.srt) srtGlobal = dados.srt;

        containerPlayer.innerHTML = `
            <div class="flex items-center justify-between mb-4 w-full">
                <p class="text-xs text-emerald-400 font-bold uppercase tracking-wider flex items-center gap-2">
                    <i class="fa-solid fa-circle-check text-base drop-shadow-[0_0_5px_rgba(16,185,129,0.8)]"></i> Áudio Finalizado
                </p>
                ${dados.srt ? `<button onclick="baixarSRT()" class="text-xs bg-[#121214] hover:bg-emerald-600 text-zinc-300 hover:text-white px-3 py-1.5 rounded-lg flex items-center gap-2 transition-colors border border-zinc-700 hover:border-emerald-500 shadow-inner group"><i class="fa-solid fa-closed-captioning group-hover:scale-110 transition-transform"></i> Baixar .SRT</button>` : ''}
            </div>
            <audio id="player_principal" controls class="w-full h-12 outline-none bg-[#09090b] rounded-lg shadow-inner"></audio>
        `;
        
        document.getElementById('player_principal').src = "data:audio/mp3;base64," + dados.audio_base64;
        document.getElementById('player_principal').play();
    } catch (e) { 
        console.error(e);
    } finally { 
        btn.classList.remove('opacity-70', 'cursor-not-allowed');
        btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> <span>Sintetizar Voz (380 coins)</span>`;
    }
}
