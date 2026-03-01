// ==========================================
// FUNÇÕES UTILITÁRIAS (PARAPHRASER / TRANSMUTER)
// ==========================================
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
    
    const elGancho = document.getElementById('nome_canal'); 
    const tituloGancho = elGancho ? elGancho.value : "";
    
    if (!textoOrig.trim()) return alert("Cole o texto original primeiro!");

    const painelResultado = document.getElementById('texto_transmutado');
    const btnTexto = document.getElementById('txt_btn_transmutar');
    
    // Tratando como TEXTAREA (Value)
    painelResultado.value = "Gerando a história com a inteligência do Gemini... Por favor, aguarde.";
    btnTexto.innerHTML = `Transmutando... <i class="fa-solid fa-circle-notch fa-spin ml-2"></i>`;

    try {
        const payload = {
            texto: textoOrig,
            tom: "Sarcástico e Ácido",
            idioma: "Português (Brasil)",
            modo: modoSelecionado,
            gancho_exato: tituloGancho
        };

        const res = await fetch('/api/v1/paraphraser', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const dados = await res.json();

        if (!res.ok) throw new Error(dados.detail || "Erro no servidor.");

        const textoGerado = dados.texto_parafrazedo || dados.texto_parafraseado || dados.texto;

        if (!textoGerado) {
            throw new Error("Falha na formatação da resposta da API.");
        }

        // SUCESSO: Insere no Value do Textarea
        painelResultado.value = textoGerado;
        
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
