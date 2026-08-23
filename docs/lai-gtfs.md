# Pedido de informação (LAI) — GTFS e dados operacionais do transporte coletivo

> Documento pronto para protocolo. Submeter pelo e-SIC de São José do Rio Preto
> (https://eic.riopreto.sp.gov.br/ ou Prefeitura → Ouvidoria / Secretaria de
> Mobilidade). Prazo legal de resposta: 20 dias, prorrogáveis por +10
> (Lei 12.527/2011, art. 15). Recurso cabível em 10 dias após resposta negativa
> (art. 16).
>
> Ao receber o feed, salvar como `data/raw/gtfs/feed.zip` e rodar
> `make transporte` — a análise sobe de OSM para GTFS automaticamente.

---

**À Secretaria de Mobilidade e Transportes / Responsável pela Lei de Acesso à
Informação do Município de São José do Rio Preto-SP**

Fundamento: **Lei Federal nº 12.527/2011** (LAI) e **Lei Estadual nº 15.240/2014**.

Solicito, com amparo no direito de acesso a informações públicas, a disponibilização,
**em formato digital aberto**, dos seguintes documentos e dados referentes ao sistema
de transporte coletivo urbano do município, operado mediante concessão/autorização
(RioPretrans/Transerp):

## 1. Dados no padrão GTFS

1.1. Arquivo completo do feed **GTFS** (*General Transit Feed Specification*) do
sistema de ônibus urbanos, contendo minimamente os arquivos `stops.txt`,
`routes.txt`, `trips.txt`, `stop_times.txt`, `calendar.txt` (ou `calendar_dates.txt`),
`agency.txt` e `shapes.txt`, na versão mais recente disponível.

1.2. Caso não exista um feed GTFS consolidado, solicito as tabelas equivalentes em
formato estruturado (CSV/XLSX/JSON): cadastro de pontos de parada com coordenadas;
itinerários das linhas com sequência de paradas; quadro de horários por dia útil,
sábado e domingo; e traçado geométrico das rotas.

## 2. Frota e operação

2.1. Quantidade de veículos da frota, por linha, com ano de fabricação.

2.2. Kilometragem programada diária por linha (oferta).

2.3. Intervalo médio (headway) por linha, nos dias úteis, em cada faixa horária.

## 3. Bilhetagem (dados agregados, sem dado pessoal)

3.1. Número de passageiros pagantes por mês, por linha, dos últimos 24 meses.

3.2. Integrações realizadas por mês (quantidade), no mesmo período.

Caso parte dos itens seja indeferida, requer-se a **resposta parcial** com os itens
atendidos, conforme art. 15, §2º do Decreto nº 7.724/2012.

Declaro que os dados solicitados não são cobertos pelas hipóteses de reserva
(arts. 21–23 da Lei 12.527) por se tratarem de informações operacionais e
estatísticas agregadas de serviço público essencial.

Local e data: São José do Rio Preto-SP, ____/____/______

Nome: _______________________________
CPF: ________________________________
E-mail: _____________________________

---

### Notas para o requerente

- **Por que GTFS?** É o padrão internacional aberto para dados de transporte.
  Com ele, esta plataforma recalcula `/transporte` com a rede oficial completa
  (todas as paradas servidas por linhas regulares), substituindo a aproximação
  via OpenStreetMap.
- **Bilhetagem agregada** serve para cruzar demanda com cobertura — nunca dados
  individuais de passageiros (que permaneceriam protegidos pela LGPD).
- Guarde o número de protocolo. Silêncio por mais de 20+10 dias é passível de
  reclamação ao Controlador-Geral e ao Ministério Público.
