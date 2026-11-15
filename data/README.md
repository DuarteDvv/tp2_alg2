# Instâncias TSPLIB

Arquivos originais, descompactados, do repositório oficial:
https://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/tspindex.html

Download realizado em 14/11/2026 a partir de `ALL_tsp.tar.gz`.

| Arquivo | Cidades | Tipo de distância |
| --- | --- | --- |
| eil51.tsp | 51 | EUC_2D |
| berlin52.tsp | 52 | EUC_2D |
| st70.tsp | 70 | EUC_2D |

Essas são as únicas três instâncias do arquivo oficial com tipo EUC_2D
e entre 10 e 75 cidades. Portanto, elas não completam as 12–16 instâncias
pedidas, nem a proporção de aproximadamente 80% com até 40 cidades.

Os exemplos ulysses16, gr24, fri26, bays29, swiss42 e att48 citados no
enunciado usam outros tipos de distância (GEO, EXPLICIT ou ATT).

Antes de completar o conjunto, confirmar com o professor se é permitido
extrair subconjuntos de cidades das instâncias EUC_2D ou alterar o critério
de seleção. Subconjuntos não herdam o custo ótimo da instância original.

Em EUC_2D, calcular cada distância como floor(sqrt(dx² + dy²) + 0.5).
