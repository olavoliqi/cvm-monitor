# CVM Monitor — Referência Claude

## O que é
Monitor diário de ofertas públicas CVM (Resolução 160 + ICVM 400/476).
Baixa CSV da CVM, filtra ofertas do dia útil anterior e envia resumo por e-mail via Gmail API (OAuth2).
Também expõe um dashboard Streamlit para consulta histórica.

## Repositório
- **GitHub:** https://github.com/olavoliqi/cvm-monitor
- **Clone local:** `C:/Users/Olavo/cvm-monitor`
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
| `gerar_tabela_html()` | Gera tabela HTML com colunas configuráveis |
| `gerar_email_html()` | Monta o corpo completo do e-mail em HTML |
| `enviar_email()` | Envia via Gmail API (OAuth2) |
| `main()` | Orquestra tudo |

## Para mudar o conteúdo do e-mail
- **Colunas exibidas:** editar as listas de tuplas `(coluna_csv, label)` dentro de `gerar_email_html()`
- **Layout/estilo:** editar os `style=` inline dentro de `gerar_tabela_html()` e `gerar_email_html()`
- **Assunto:** editar a variável `assunto` em `main()`
- **Texto introdutório/rodapé:** editar o HTML em `gerar_email_html()`

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
# Editar arquivos em C:/Users/Olavo/cvm-monitor
git -C C:/Users/Olavo/cvm-monitor add <arquivo>
git -C C:/Users/Olavo/cvm-monitor commit -m "mensagem"
git -C C:/Users/Olavo/cvm-monitor push
```
O Streamlit Cloud faz redeploy automático após o push.
