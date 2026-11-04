# INF0336 - Seminário

## Máquinas Virtuais x Contêineres

## Equipe: queremos emprego
202301431 - Danilo Lourenço Macedo Dias <br>
202301437 - Felipe do Espirito Santo Sabino <br>
202401773 - Gabriel dos Santos Oliveira <br>
202103785 - Wevton Junior Fagundes Santana

## Apresentações
1. [Apresentação 1](https://docs.google.com/presentation/d/1eixvtAASkLtC9iFD6saS6Op2AYg7gExORQ_1SO6LLiE/edit?slide=id.g1619b4b1478_0_160#slide=id.g1619b4b1478_0_160) <br>
2. [Apresentação 2](https://docs.google.com/presentation/d/1ICUxV39he5M6L8Q5ocgflnhrpJmuoMaQnYiOIuaaYek/edit?slide=id.h1b1034c9d852efe2_1_0#slide=id.h1b1034c9d852efe2_1_0) <br>

## Resumo
Máquinas virtuais e contêineres oferecem diferentes formas de isolamento de aplicações, que podem influenciar o desempenho e o consumo de recursos. Este projeto tem como objetivo comparar a execução de um mesmo programa em ambiente nativo, em um contêiner e em uma máquina virtual. Serão realizados testes repetidos sob condições controladas, utilizando o GNU Time para medir o tempo total de execução, o tempo de CPU, a utilização média de CPU e o pico de memória residente. Os resultados serão comparados com a execução nativa e discutidos com base na literatura. Espera-se identificar diferenças de desempenho e consumo de recursos entre os ambientes para a carga de trabalho escolhida. 

## Introdução
A introdução deve ter as seguintes partes: <br>
- **Motivação:** É aqui que você apresenta a ideia por trás do seu projeto. Recomenda-se uma narrativa do geral para o específico, começando com uma descrição ampla do tema e avançando para paradigmas, experimentos, aplicações ou fenômenos mais detalhados que serão estudados.
- **Revisão bibliográfica:** Pesquise o tema utilizando, pelo menos, cinco fontes (as mesmas que devem ser úteis para a seção de Discussão). Utilize fontes confiáveis, por exemplo, Google Acadêmico ou publicações revisadas por pares (blogs, repositorios, publicações online, etc.).
- **Objetivos:** Qual é o propósito do projeto no qual você trabalhará ao longo das próximas cinco semanas? Exemplo: entender e aplicar o conceito de ..., experimentar um conjunto de tecnologias (*software stack*), analisar o estado da arte em ..., etc.

### Objetivos

Comparar o tempo total de execução, o tempo de CPU, a utilização média de CPU e o pico de memória residente de uma aplicação nos três ambientes. Os testes serão realizados sob condições controladas e com repetições, permitindo analisar a variabilidade dos resultados e relacioná-los à literatura.

## Metodologia

### Conjunto de dados e experimentos

Os dados serão produzidos pela equipe por meio da execução de um mesmo programa em três ambientes: nativo, contêiner e máquina virtual. Serão utilizadas entradas de diferentes tamanhos, mantendo os mesmos dados de entrada nos três ambientes. O programa e os tamanhos das entradas serão definidos na etapa de preparação.

Cada combinação de ambiente e entrada será uma condição experimental, executada repetidas vezes. Os resultados serão registrados em tabelas e analisados por meio de estatísticas descritivas, como média, mediana e desvio-padrão, permitindo comparar o desempenho e a variabilidade das medições.

### Modelos e infraestrutura

Os experimentos serão realizados em uma mesma máquina física, com Linux, utilizando execução nativa, contêiner Docker e uma máquina virtual Linux. A ferramenta de virtualização será definida e documentada durante a preparação dos ambientes.

Serão mantidas versões equivalentes do programa e de suas dependências, além do mesmo número de threads e condições comparáveis de acesso aos recursos. As configurações de hardware, software, CPU e memória serão registradas para permitir a reprodução dos testes.

Antes das medições, serão realizados testes de validação da saída e aquecimento. As execuções ocorrerão uma por vez, alternando a ordem dos ambientes e reduzindo atividades em segundo plano. O tempo de inicialização dos ambientes não fará parte das medições.

### Métricas

A coleta será realizada com o GNU Time, utilizando o comando `/usr/bin/time -v ./prog` dentro de cada ambiente. Serão consideradas as seguintes métricas:

- **Tempo total de execução:** tempo decorrido entre o início e o término do programa, incluindo processamento e esperas.
- **Tempo de CPU:** soma dos tempos de processamento em modo usuário (*User time*) e em modo kernel (*System time*).
- **Utilização média de CPU:** relação percentual entre o tempo de CPU e o tempo total de execução.
- **Pico de memória residente:** maior quantidade de memória do processo residente na RAM durante a execução.

As medições representam os recursos utilizados pela aplicação, não o consumo total da infraestrutura, como o sistema operacional da máquina virtual. Os resultados serão comparados com a execução nativa, considerando as diferenças percentuais e a variabilidade entre repetições, e discutidos com base na literatura.

## Fluxograma
![Fluxograma da metodologia](Fluxograma.png)

## Resultados
- Gráficos
- Tabelas
- Multimídia (vídeos, imagens, áudio)

## Discussão
Análise com base na literatura utilizada na seção de Introdução!

## Conclusão
Em que medida o(s) objetivo(s) foi(foram) alcançado(s)?

## Referências
No formato ABNT
