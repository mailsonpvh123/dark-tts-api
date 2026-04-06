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
let histDadosAtuais = []; // Para resgatar detalhes sem bater na API de novo

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
            if (path === '/audio-mixer') icon.classList.add('text-teal-400');
            if (path === '/meta-seo') icon.classList.add('text-blue-400');
            if (path === '/thumb-maker') icon.classList.add('text-rose-400');
            if (path === '/historico') icon.classList.add('text-emerald-400');
        }
    });

    if (path === '/historico') {
        carregarHistorico();
    }
});

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
        
        histDadosAtuais = data.historico; // Salva o cache
        
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

        // Atualiza Informações de Paginação
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
    
    // Atualiza botões
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

    // Reset Ações
    acoesContainer.innerHTML = '';
    
    // Tratamento de Áudio vs Texto
    if (reg.ferramenta.includes("Voice")) {
        // A mágica de suportar MP3 e SRT se eles estiverem salvos juntos (ex: path_mp3|texto_srt)
        // Se no BD salvamos só o MP3: "/static/audios/..."
        // Mas se quisermos suportar o SRT que foi gerado na mesma hora, ele deve estar salvo no banco (o Python precisaria ter concatenado, ex: `/static/audios/...|1\n00:00...`)
        // Caso não tenhamos o SRT no BD deste registro antigo, só mostramos o áudio.
        
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

        // Botões de Áudio
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
        // É Texto
        outputContainer.innerHTML = `<pre id="texto_resgate" class="text-sm text-zinc-300 font-mono whitespace-pre-wrap p-6 relative z-10 max-h-64 overflow-y-auto custom-scrollbar">${reg.resultado}</pre>`;
        
        // Botões Padrão de Texto
        acoesContainer.innerHTML = `
            <button onclick="copiarTextoHist()" class="col-span-1 py-3 bg-[#18181b] hover:bg-emerald-600 hover:border-emerald-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                <i class="fa-solid fa-copy"></i> Copiar
            </button>
            <button onclick="baixarTxtHist('${reg.ferramenta}', '${reg.data_formatada}')" class="col-span-1 py-3 bg-[#18181b] hover:bg-zinc-700 hover:border-zinc-500 border border-zinc-800 text-zinc-300 hover:text-white rounded-xl font-bold text-xs transition-all flex justify-center items-center gap-2 shadow-sm">
                <i class="fa-solid fa-file-arrow-down"></i> .TXT
            </button>
        `;

        // Botões Especiais de Encaminhamento (Esteira)
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

    modal.classList.remove('hidden');
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

// Lógica para enviar dados de uma ferramenta para outra
function encaminharPara(destino, index) {
    const reg = histDadosAtuais[index];
    const texto = reg.resultado;
    
    if (destino === 'script') {
        // Pega só o texto pra ideia base
        sessionStorage.setItem('script_ideia_base', texto);
        window.location.href = '/script-forge';
    } else if (destino === 'voice') {
        sessionStorage.setItem('voice_texto', texto);
        window.location.href = '/voice-synthesizer';
    } else if (destino === 'seo') {
        sessionStorage.setItem('seo_roteiro', texto);
        window.location.href = '/meta-seo';
    }
}
