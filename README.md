# TP2 — Algoritmos 2

Implementação modular em Python 3.11 ou superior. NetworkX é usado apenas
para o emparelhamento perfeito de peso mínimo do Christofides.

Prepare o ambiente na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Executar uma instância

```bash
python -m src.main data/eil51.tsp --strategy hull --time-limit 10
```

As cinco estratégias são `trivial`, `nearest`, `hull`, `twice` e
`christofides`. O padrão é `nearest`; o tempo padrão é 1800 segundos.
Use `--initial-only` para construir a rota sem executar a busca exata.

## Branch-and-Bound

A busca é em profundidade e fixa a cidade inicial em 0. Em cada estado,
o limite inferior é o custo já percorrido mais:

1. O custo da MST dos vértices ainda não visitados.
2. A menor ligação da cidade atual a esses vértices.
3. A menor ligação desses vértices à cidade inicial.

Qualquer conclusão da rota custa pelo menos esse valor. Se o limite é
maior ou igual ao custo da melhor rota conhecida, o estado é podado.
Os próximos vértices são explorados por distância crescente. A matriz
é compartilhada entre estados; não há cópias de matrizes nem cache de
subconjuntos que possa crescer exponencialmente. As listas de candidatos
ficam na pilha da busca. O tempo no pior caso continua exponencial.

O limite inferior requer distâncias simétricas e não negativas, mas não
depende da desigualdade triangular. As garantias clássicas de aproximação
do Twice e do Christofides requerem essa desigualdade; o arredondamento
EUC_2D pode violá-la em alguns conjuntos de pontos.

## Experimentos

Todas as instâncias de `data/`, com as cinco inicializações:

```bash
python -m src.experiments --time-limit 1800 --repetitions 3 --output results/bnb.csv
```

Isso agenda 45 execuções: no limite, cerca de 22,5 horas de busca.
Para escolher instâncias e estratégias:

```bash
python -m src.experiments data/eil51.tsp --strategies trivial hull --time-limit 60
```

Para medir memória, faça uma coleta separada, pois `tracemalloc` interfere
no tempo e no número de estados que cabem no orçamento:

```bash
python -m src.experiments --memory --output results/bnb_memory.csv
```

Para avaliar somente as cinco rotas iniciais e suas subrotinas:

```bash
python -m src.experiments --initial-only --memory --output results/initial_memory.csv
```

O CSV é atualizado após cada execução e novas execuções são acrescentadas
ao arquivo existente. Reexecutar um comando repete os experimentos; não
há retomada automática. Os arquivos `results/smoke_*.csv` são verificações
rápidas de integração, não a coleta final do trabalho.

### Métricas

- `status`: `optimal` (ótimo comprovado), `timeout` ou `heuristic` (sem busca).
- `optimal_cost`: custo ótimo quando comprovado; `NA` nos outros casos.
- `best_cost`, `initial_cost`, `route`: melhor solução viável e inicialização.
- `initial_seconds`, `search_seconds`, `total_seconds`: tempo da inicialização,
  da busca e total, respectivamente. O total inclui leitura e matriz.
- `nodes_expanded`: estados não terminais que passaram pela poda e geraram ramificações.
- `nodes_pruned`: estados descartados pelo custo ou limite inferior.
- `complete_routes`: estados terminais avaliados.
- `max_depth`: maior quantidade de arestas fixadas desde a origem.
- `bound_calls`, `bound_seconds`: chamadas e tempo acumulado do limite inferior,
  incluindo a MST. Uma chamada interrompida também entra na medição.
- Tempos separados de leitura, matriz, fecho convexo, inserção, MST inicial,
  emparelhamento (incluindo montagem de seu grafo) e circuito com atalhos.
- `peak_bytes`: pico de alocações Python da execução, quando `--memory` está ativo.
  Os campos de memória por etapa medem o pico adicional sobre as alocações
  existentes no início daquela etapa. Não representam a memória RSS do processo.
- Versões de Python e NetworkX, instante UTC, limite e número da repetição.

Etapas não utilizadas e memória não medida recebem `NA`, não zero. Os tempos
de subrotinas estão contidos nos tempos maiores; não devem ser somados a eles.
As rotas do CSV usam índices a partir de 0 e não repetem a origem ao final.

O orçamento de até 30 minutos inclui preparação e inicialização. A interrupção
é cooperativa, com checagens em cada estado e dentro do Prim da busca. Uma
inicialização já em andamento termina antes da checagem, portanto o limite
não é um encerramento rígido do processo. Em timeout, custos e contadores
parciais são preservados, mas não se declara otimalidade.

## Testes

```bash
python -m unittest discover -s tests -v
```

Os testes comparam as cinco inicializações e a busca com força bruta em
casos pequenos, além de conferir timeout, casos degenerados, emparelhamento
e exportação das métricas.

## Organização

- `src/instance.py`: leitura de arquivos EUC_2D e matriz de distâncias.
- `src/routes.py`: validação e custo de rotas, incluindo o retorno ao início.
- `src/heuristics.py`: construção das rotas iniciais.
- `src/convex_hull.py`: fecho convexo e inserção gulosa.
- `src/mst.py`: Prim sobre a matriz de distâncias.
- `src/approximations.py`: Twice-around-the-tree e Christofides.
- `src/branch_and_bound.py`: busca exata, poda e contadores.
- `src/profiling.py`: medição de etapas da inicialização.
- `src/experiments.py`: execução em lote e exportação CSV.
- `src/main.py`: execução pela linha de comando.
- `tests/`: verificações automatizadas.
- `data/`: instâncias e observações sobre a seleção.

Internamente, as cidades são índices de 0 a N-1 na ordem das coordenadas
do arquivo. A rota guarda cada cidade uma vez; o retorno ao início é
incluído no cálculo do custo e na exibição.

Ainda faltam completar o conjunto de instâncias, executar as coletas finais,
extrair as características geométricas para análise de sensibilidade,
ajustar os modelos estatísticos e produzir o artigo.

Referência da biblioteca: [emparelhamento mínimo no NetworkX](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.matching.min_weight_matching.html).
