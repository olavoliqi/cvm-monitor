# CVM Monitor

Monitor diario de ofertas publicas da CVM (Resolucao 160 mais ICVM 400/476).
Baixa o CSV da CVM, filtra as ofertas do dia util anterior e manda resumo por
e-mail pela Gmail API. Tambem expoe um dashboard Streamlit para consulta
historica.

**Status:** em producao. Ultimo ajuste em 07/10/2026 (destinatarios novos e keepalive sem action de terceiro).
**Doc mestre:** `CLAUDE.md`.

## Como retomar
Abrir `CLAUDE.md`. Ele tem a estrutura, as variaveis de ambiente e o deploy.

## O que esta aqui
| item | o que e |
|---|---|
| `CLAUDE.md` | referencia do projeto, documento mestre |
| `cvm_monitor.py` | baixa, filtra, gera e envia o e-mail |
| `app.py` | dashboard Streamlit |
| `setup_oauth.py` | configura o OAuth2 do Gmail (roda uma vez) |
| `preview_*.html` | previews do e-mail |

## Onde vive
- GitHub: https://github.com/olavoliqi/cvm-monitor (branch `master`)
- Dashboard: https://cvm-monitor-irbqwb5qenqvuulsfgrtbh.streamlit.app/

## Atencao
As credenciais vem de **variavel de ambiente** (`GMAIL_REFRESH_TOKEN`,
client id e secret), nao de arquivo. Existe uma copia velha deste projeto em
`liqi/_arquivo/scripts/cvm-monitor/` com um `credentials.json` antigo: **nao e a
versao viva** e nao deve ser usada.
