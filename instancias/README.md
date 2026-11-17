# Instâncias

Fonte: [TSPLIB](https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/tspindex.html).

- `principal/`: 9 subconjuntos ATT/EUC_2D e 3 GEO originais: burma14, ulysses16 e ulysses22
- `estresse/`: 3 instâncias com 41 a 75 cidades: att48, berlin52 e st70

- `.tsp`: dados do problema
- `.opt.tour`: rota ótima de referência

Os subconjuntos usam as primeiras cidades dos arquivos originais:

| Subconjunto | Origem | Cidades selecionadas |
| --- | --- | --- |
| att48_sub10 | att48 | 1 a 10 |
| att48_sub18 | att48 | 1 a 18 |
| att48_sub26 | att48 | 1 a 26 |
| att48_sub34 | att48 | 1 a 34 |
| berlin52_sub14 | berlin52 | 1 a 14 |
| berlin52_sub20 | berlin52 | 1 a 20 |
| st70_sub16 | st70 | 1 a 16 |
| st70_sub24 | st70 | 1 a 24 |
| st70_sub30 | st70 | 1 a 30 |

Os subconjuntos preservam o tipo de distância da origem e não herdam seu ótimo.
Subconjuntos da mesma origem compartilham cidades e não são amostras independentes.


As rotas `.opt.tour` fornecem as referências de ótimo quando disponíveis.
Para GEO, o fecho e as features usam projeção equiretangular centrada na região;
os custos usam sempre a fórmula GEO da TSPLIB.
A seleção de ATT, GEO e de subconjuntos ainda precisa ser alinhada com o professor,
pois o enunciado exige literalmente EUC_2D.
