# CVM Monitor — Referência Claude

## O que é
Monitor diário de ofertas públicas CVM (Resolução 160 + ICVM 400/476).
Baixa CSV da CVM, filtra ofertas do dia útil anterior e envia resumo por e-mail via Gmail API (OAuth2).
Também expõe um dashboard Streamlit para consulta histórica.

## Repositório
- **GitHub:** https://github.com/olavoliqi/cvm-monitor
- **Clone local:** `C:/Users/Olavo Meyer/Claude Code files/cvm-monitor` (branch `master`)
- **Deploy (dashboard):** https://cvm-monitor-irbqwb5qenqvuulsfgrtbh.streamlit.app/

## Estrutura de arquivos
```
cvm_monitor.py   # Script principal: baixa CSV, filtra, gera e envia e-mail
app.py           # Dashboard Streamlit (consulta histórica com filtros)
setup_oauth.py   # Utilitário para configurar OAuth2 Gmail
requirements.txt # Dependências Python: requests, pandas, streamlit==1.41.0
.env.example     # Exemplo de variáveis de ambiente necessárias
```

## Variáveis de ambiente (.env / Secrets do Codespace)
```
GMAIL_ADDRESS=olavo@liqi.com.br, flavio.altimari@liqi.com.br
GMAIL_CLIENT_ID=...
GMAIL_CLIENT_SECRET=...
GMAIL_REFRESH_TOKEN=...
```

## Emails cadastrados para envio diário
- olavo@liqi.com.br
- flavio.altimari@liqi.com.br

> Para adicionar/remover destinatários: editar `GMAIL_ADDRESS` no `.env` / Secrets do Codespace.
> O campo `To` do e-mail está hardcoded em `enviar_email()` — atualizar junto se necessário.

## Funções principais em cvm_monitor.py
| Função | O que faz |
|---|---|
| `dia_util_anterior()` | Calcula o dia útil anterior (considera feriados BR) |
| `baixar_csvs()` | Baixa e descompacta o ZIP da CVM |
| `filtrar_ofertas_res160()` | Filtra ofertas Resolução 160 por data |
| `filtrar_ofertas_distribuicao()` | Filtra demais ofertas (ICVM 400/476) por data |
| `limpar_texto()` | Normaliza espaços e trunca campos de texto livre da CVM |
| `gerar_tabela_html()` | Gera tabela HTML com colunas configuráveis |
| `gerar_email_html()` | Monta o corpo completo do e-mail em HTML |
| `enviar_email()` | Envia via Gmail API (OAuth2) |
| `main()` | Orquestra tudo |

## Layout do e-mail (duas linhas por oferta)

Cada oferta ocupa **duas linhas** na tabela:

1. **Linha principal** — campos curtos, definidos em `COLS_RES160` / `COLS_DIST`.
2. **Linha de detalhe** (colspan, fundo cinza) — campos descritivos e
   prestadores, definidos em `DET_RES160` / `DET_DIST`, rotulados em azul Liqi.

Esse desenho existe porque a Resolução 160 traz 20+ campos relevantes: em
colunas de verdade a tabela estouraria a largura de qualquer cliente de e-mail.
Campos vazios na base da CVM são omitidos da linha de detalhe (não aparece "—").

### Para mudar o conteúdo do e-mail
- **Colunas da linha principal:** editar `COLS_RES160` / `COLS_DIST`
- **Campos da linha de detalhe:** editar `DET_RES160` / `DET_DIST`
- **Formatação de célula:** `formatar_celula()` — decide entre texto longo
  truncado (`CAMPOS_LONGOS`), moeda (`CAMPOS_VALOR`) e S/N (`MAPA_SN`)
- **Layout/estilo:** constantes `_TH`, `_TD`, `_TD_DET` e o HTML de
  `gerar_email_html()`
- **Assunto:** variável `assunto` em `main()`

### Preview local sem enviar e-mail
Rodar `gerar_email_html()` com um DataFrame filtrado e salvar em HTML. Sem as
variáveis OAuth no ambiente, `enviar_email()` já não envia nada — só imprime.

## ⚠️ Campos de texto livre (devedores, lastro, destinação, garantias)
As colunas `Identificacao_devedores_coobrigados`, `Descricao_lastro`,
`Destinacao_recursos`, `Descricao_garantias` e `Ativos_alvo` existem **apenas**
em `oferta_resolucao_160.csv`. O `oferta_distribuicao.csv` (ICVM 400/476) **não
tem** esses campos, nem público-alvo, nem regime de distribuição — não adicionar
na tabela de "Demais Ofertas". O e-mail traz uma nota explícita nessa seção.

São textos preenchidos livremente pelo emissor (média 150–260 caracteres, casos
de 3.000+). Passam por `limpar_texto()`, que colapsa espaços/quebras e trunca em
`MAX_CHARS_CAMPO_LONGO` (400). O texto integral fica no dashboard Streamlit.

**Não subir muito o truncamento:** o Gmail corta ("mensagem truncada") o corpo
acima de ~102 KB. Com 400 caracteres e 17 ofertas o e-mail fica em ~46 KB;
a 1.500 caracteres passaria de 100 KB e seria cortado.

### Campos de "regime"
A CVM tem dois, e ambos vão no e-mail:
- `Regime_distribuicao` — garantia firme vs. melhores esforços (linha principal)
- `Regime_fiduciario` — S/N (linha de detalhe)

## Fonte de dados
- URL: https://dados.cvm.gov.br/dados/OFERTA/DISTRIB/DADOS/oferta_distribuicao.zip
- Atualizado a cada hora pela CVM
- Encoding: latin-1 · Separador: ;

## ⚠️ IMPORTANTE — IPv4 obrigatório no download
O `dados.cvm.gov.br` é dual-stack e responde com um IPv6 brasileiro (bloco
`2804::`) que hosts fora do Brasil (GitHub Actions, Streamlit Cloud) NÃO
conseguem rotear → `[Errno 101] Network is unreachable`. Por isso, tanto
`cvm_monitor.py` quanto `app.py` forçam IPv4 no import:
```python
import socket, urllib3.util.connection as urllib3_cn
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET
```
NÃO remover essas linhas — sem elas o robô e o dashboard voltam a quebrar
em qualquer ambiente hospedado fora do Brasil.

## ⚠️ Não arquivar o repositório no GitHub
Arquivar o repo o deixa read-only, DESATIVA os workflows agendados
(aparecem como `disabled_manually`) e derruba o robô diário. O dashboard
Streamlit também dorme. Se precisar reativar: `gh api -X PATCH
repos/olavoliqi/cvm-monitor -f archived=false`, depois `gh workflow enable`
nos dois workflows e reboot do app no painel do Streamlit.

## Workflow para editar e publicar
```bash
# Editar arquivos em "C:/Users/Olavo Meyer/Claude Code files/cvm-monitor"
cd "C:/Users/Olavo Meyer/Claude Code files/cvm-monitor"
git add cvm_monitor.py app.py CLAUDE.md   # nunca `git add -A` (o .venv/ mora aqui)
git commit -m "mensagem"
git pull --rebase
git push
```
O Streamlit Cloud faz redeploy automático após o push.
