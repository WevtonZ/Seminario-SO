import csv
from pathlib import Path

PASTA = Path(__file__).parent
CSVS = Path(__file__).parent.parent
CSVS = CSVS / "resultados"

ARQUIVOS = {
    "vm.csv": "vm",
    "nativo.csv": "nativo",
    "docker.csv": "docker",
}

cabecalho = None
linhas = []

for nome, ambiente in ARQUIVOS.items():
    with open(CSVS / nome, newline="", encoding="utf-8") as f:
        leitor = csv.reader(f)
        cab = next(leitor)

        if cabecalho is None:
            cabecalho = cab
        elif cab != cabecalho:
            raise ValueError(f"Colunas de {nome} diferem das demais: {cab}")

        for linha in leitor:
            if linha:
                linhas.append(linha + [ambiente])

with open(PASTA / "merged.csv", "w", newline="", encoding="utf-8") as f:
    escritor = csv.writer(f)
    escritor.writerow(cabecalho + ["ambiente"])
    escritor.writerows(linhas)