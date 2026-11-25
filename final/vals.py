# separar os caras por N, pra cada N, separar pela variante

# calcular pra cada grupo a curva de gauss, ver se eh   
# pra cada grupo (N,variante), calcular: media, desvio padrao amostral e tratamento de discrepancias

# elaborar diagramas
# grafico de dispersao, pra cada grupo fazer de uma cor e fazer com todas as medidas
# grafico de caixa vou fazer com a media ou com todas as medidas?
# grafico de radar vou fazer com a media
# grafico de barras vou fazer com a media


import numpy as np
import pandas as pd

ENTRADA = "merged.csv"
SAIDA = "resultados.csv"

IQR_FATOR = 1.5          # limites: Q1 - 1,5*IQR e Q3 + 1,5*IQR
IQR_MIN_RESOLUCOES = 1   # se IQR <= isso x resolução da métrica, não remove nada

METRICAS = [
    "tempo_total",
    "tempo_usuario",
    "tempo_sistema",
    "tempo_cpu",
    "utilizacao_cpu",
    "pico_memoria_kib",
]

# ---------------------------------------------------------------- leitura
# N é lido como texto para manter rótulos como "1e3"; N_num serve para ordenar
df = pd.read_csv(ENTRADA, dtype={"N": str})
df["N_num"] = df["N"].astype(float)
df["utilizacao_cpu"] = df["utilizacao_cpu"].str.rstrip("%").astype(float)

# Resolução de cada métrica: menor diferença não nula entre valores distintos
# (ex.: 0,01 s nos tempos, 1 ponto percentual na utilização, 4 KiB na memória)
RESOLUCAO = {}
for m in METRICAS:
    diferencas = np.diff(np.sort(df[m].unique()))
    RESOLUCAO[m] = diferencas[diferencas > 1e-9].min()


# ---------------------------------------------------------------- função
def mascara_outliers_iqr(x, resolucao):
    """Marca outliers pelo IQR. Se o IQR for 'quase zero', não marca nenhum.
    Retorna (mascara, iqr, aplicado)."""
    q1, q3 = np.percentile(x, [25, 75])
    iqr = q3 - q1
    # tolerância evita erro de ponto flutuante (ex.: 0,0100000001 > 0,01)
    if iqr <= IQR_MIN_RESOLUCOES * resolucao + 1e-9:
        return np.zeros(len(x), dtype=bool), iqr, False
    return (x < q1 - IQR_FATOR * iqr) | (x > q3 + IQR_FATOR * iqr), iqr, True


# ---------------------------------------------------------------- análise
linhas = []

for (_, n, variante, ambiente), sub in df.groupby(["N_num", "N", "variante", "ambiente"]):
    for metrica in METRICAS:
        x = sub[metrica].to_numpy(dtype=float)

        outlier, iqr, aplicado = mascara_outliers_iqr(x, RESOLUCAO[metrica])
        x_limpo = x[~outlier]

        linhas.append({
            "N": n,
            "variante": variante,
            "ambiente": ambiente,
            "metrica": metrica,
            "n": len(x),
            "iqr": iqr,
            "iqr_aplicado": aplicado,
            "n_outliers": int(outlier.sum()),
            "media_bruta": x.mean(),
            "desvio_bruto": x.std(ddof=1),
            "media": x_limpo.mean(),
            "desvio": x_limpo.std(ddof=1),
        })

res = pd.DataFrame(linhas)
res.to_csv(SAIDA, index=False)