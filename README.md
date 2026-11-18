# TP2 — Algoritmos 2

Python 3.11+ em Linux/macOS. Preparação:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Um experimento por vez

Escolha uma instância e uma inicialização:

```bash
.venv/bin/python -m src.main att48_sub10 --strategy trivial
```

O comando executa **somente esse caso**, com limite de 30 minutos,
mostra um resumo e salva a medição em `results/tempos.csv`.
Não inicia outras instâncias nem outras estratégias automaticamente.

Para a próxima inicialização, execute outro comando:

```bash
.venv/bin/python -m src.main att48_sub10 --strategy nearest
```

| Estratégia | Inicialização |
| --- | --- |
| trivial | Ordem das cidades no arquivo |
| nearest | Vizinho mais próximo |
| hull | Fecho convexo com inserção |
| twice | Twice-around-the-tree |
| christofides | Christofides |

Repita para as cinco estratégias de cada uma das 15 instâncias.
O nome pode ser informado com ou sem `.tsp`, ou como caminho completo.

## Opções

- `--time-limit 60`: muda o limite para 60 segundos; padrão: 1800.
- `--no-time-limit`: busca sem limite para descobrir o ótimo. Salve essas
  execuções separadamente com `--output results/sem_limite.csv`.
- `--memory`: mede memória e salva em `results/memoria.csv`. Faça essa rodada
  separada, pois a medição interfere nos tempos.
- `--initial-only`: executa apenas a heurística escolhida, sem Branch-and-Bound.
- `--output results/outro.csv`: escolhe o arquivo de saída.

Por exemplo, para avaliar Christofides sozinho:

```bash
.venv/bin/python -m src.main att48 --strategy christofides --initial-only
```

## Resultados

O CSV guarda custos e rotas iniciais e finais, tempos, nós visitados,
expandidos e podados, profundidades, características geométricas,
violações triangulares e profiling das subrotinas. Com `--memory`, também
registra picos de alocações Python, não a memória RSS do processo.
O pico de cada subrotina é o maior acréscimo sobre a memória viva na sua
entrada; não some esses picos. A rodada com memória também respeita 30 minutos,
mas a instrumentação pode fazer a busca atingir esse limite mais cedo.

- `peak_bytes`: pico total da execução, incluindo leitura e preparação.
- `read_peak_bytes`: pico adicional da leitura do arquivo.
- `subroutine_peak_bytes`: maior pico adicional das subrotinas, excluindo
  a leitura. É o máximo das colunas por etapa, incluindo a construção da matriz;
  não representa a memória total simultânea do algoritmo.

Os custos de referência são calculados diretamente das rotas `.opt.tour`,
quando disponíveis. Não é necessário criar ou preencher outra tabela.
Para os subconjuntos, o ótimo só é conhecido quando o Branch-and-Bound
conclui. Sem referência, o gap fica `NA`.

Depois de coletar os casos, este comando usa os ótimos comprovados em uma
execução para completar os gaps das demais no próprio CSV:

```bash
.venv/bin/python -m src.results results/tempos.csv
```

Os dados ficam em apenas dois arquivos: `results/tempos.csv` e
`results/memoria.csv`. Cada um contém as métricas, referências e gaps.

Timeouts mantêm soluções viáveis e contadores parciais, mas não declaram
ótimo. O limite inclui leitura, matriz, inicialização e busca. Features e
escrita do CSV ficam fora do tempo do algoritmo. Não some os tempos das
subrotinas ao total, pois já estão incluídos nele.

Repetir a mesma instância, estratégia, modo e limite substitui a medição
anterior no arquivo escolhido. Para guardar repetições, use outro `--output`.
CSVs antigos com outras colunas são recusados: use outro arquivo de saída.

## Código

- `src/main.py`: comando para um experimento.
- `src/runner.py`: execução e coleta das métricas.
- `src/instance.py`: arquivos, distâncias EUC_2D/ATT/GEO e rotas de referência.
- `src/branch_and_bound.py`: busca exata.
- `src/heuristics.py`, `src/approximations.py`, `src/convex_hull.py`, `src/mst.py`: construção de rotas.
- `src/profiling.py`, `src/timeout.py`: medições e limite de tempo.
- `src/features.py`: características geométricas e topológicas.
- `src/results.py`: gravação do CSV e cálculo dos gaps.

Em GEO, o fecho e as features usam uma projeção equiretangular centrada na
região das cidades. Inserções, rotas, MST e matching usam as distâncias GEO
originais. A projeção pode alterar o fecho; não é um fecho esférico.

O conjunto usa ATT, GEO e subconjuntos por decisão do projeto; isso ainda precisa
ser alinhado com o professor em relação à exigência literal de EUC_2D.
Subconjuntos da mesma origem compartilham cidades e não são independentes.
As garantias de Twice e Christofides exigem desigualdade triangular;
o arredondamento EUC_2D pode violá-la. O Branch-and-Bound não depende dela.
