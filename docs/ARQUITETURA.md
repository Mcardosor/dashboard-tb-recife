# Arquitetura — TB Recife

Visão de ponta a ponta pra quem for rodar, estender ou dar manutenção neste projeto sem ajuda direta de quem construiu.

## Fluxo de dados

```
PostgreSQL (base "cenarios_ai", schema dados_geolink.Recife_PE_geolink_TB —
SINAN-TB cruzado com SIM e geocodificado por bairro/distrito/setor censitário)
        │
        │  export único, via VPN (script fora deste repositório)
        ▼
dados_dashboard/recife_tb_geolink.parquet   (26.050 linhas, 289 colunas)
dados_dashboard/recife_tb_sinan.parquet
dados_dashboard/obitos_sim_recife.parquet
dados_dashboard/pop_recife.parquet
dados_dashboard/bairros_recife.geojson
        │
        ▼
src/banco.py  ──►  DuckDB lê o Parquet local (só as colunas de COLUNAS_DASHBOARD)
        │
        ▼
src/indicadores.py (cálculos epidemiológicos) + src/graficos.py + src/mapa.py
        │
        ▼
app.py  ──►  sidebar, KPIs, abas
        │
        ▼
Streamlit renderiza no navegador
```

**Limitação conhecida (importante):** diferente do TB SINAN nacional, **este repositório não contém o pipeline** que gera os Parquet a partir do Postgres — o export (`exportar_recife.py`, mencionado no planejamento do projeto) roda fora daqui, uma única vez, via VPN. Os dados em `dados_dashboard/` são um **snapshot congelado** (2010–2023). Pra atualizar, é preciso reconstruir esse script de export e rodá-lo de novo com acesso à VPN/Postgres — não há como fazer isso só com o conteúdo deste repo.

## Módulos

| Arquivo | Responsabilidade |
|---|---|
| `app.py` | Entrada Streamlit — sidebar, KPIs, seções |
| `src/banco.py` | Engine DuckDB sobre o Parquet local (nome "banco" é histórico — não há conexão de banco ao vivo aqui) |
| `src/indicadores.py` | Cálculos epidemiológicos (incidência, cura, abandono, coinfecção) |
| `src/graficos.py` | Construtores Plotly |
| `src/mapa.py` | Mapa por bairro/Distrito Sanitário (Folium + streamlit-folium) |
| `src/constantes.py` | Caminhos dos Parquet, colunas usadas, paletas |
| `src/styles.py` | CSS Cenários+ e toggle dark/light |

## Ambiente e variáveis

Nenhuma variável de ambiente é necessária pra rodar o app — os dados já vêm como Parquet estático, sem conexão a banco em tempo de execução. `STREAMLIT_SERVER_BASE_URL_PATH=cenarios/tbrecife` é setado só no `docker-compose.yml` (produção); em desenvolvimento local o `.streamlit/config.toml` roda sem `baseUrlPath`.

## Deploy

- **Imagem:** `docker-compose.yml` builda a partir do `Dockerfile`, com `dados_dashboard/` bind-mounted (`:ro`) por cima — trocar os Parquet no host reflete sem rebuild.
- **Container:** `dashboard-tb-recife`, porta **8503**.
- **Produção (VM):** `/home/matheusrodrigues/dashboard-tb-recife/`, exposto via nginx em `https://painel.cenarios.unb.br/cenarios/tbrecife` (proxy_pass pra `localhost:8503`).

## Limitações conhecidas

- Pipeline de exportação (Postgres → Parquet) não está neste repositório (ver seção Fluxo de dados).
- Cobertura: 2010–2023, só o município de Recife (PE); 99 bairros, 8 Distritos Sanitários, 2.447 setores censitários.
- Vinculação SINAN-SIM tem ~2.340 registros com link de óbito; nem todo caso tem desfecho de óbito vinculado.
- **A aba Análise Livre não funciona ainda.** A migração de PyGWalker para
  Apache Superset foi feita no código, mas o iframe aponta para um
  `datasource_id` que é literalmente o texto `PENDENTE_CONECTAR_DATASET_RECIFE`.
  Faltam três passos, todos na VM (ver comentário em `app.py`, seção Análise
  Livre): conectar `recife_tb_geolink.parquet` como dataset no Superset,
  substituir o placeholder pelo id gerado, e confirmar que a rota
  `/cenarios/tbrecife` também expõe `/cenarios/superset/`. Até lá a aba carrega
  um iframe que o Superset rejeita.
- O painel **não tem download em CSV**, apesar de versões antigas desta
  documentação mencionarem um.
- Sem testes automatizados. O painel de PE (`Tuberculose_Pernambuco`) e o TB
  nacional (`tuberculose-sinan`) já têm suítes de invariante epidemiológico;
  trazer a mesma abordagem para cá é o maior ganho disponível neste repositório.
