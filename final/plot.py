from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.colors import TwoSlopeNorm

# métrica -> (título do painel, unidade)
METRICAS = {
    "tempo_total": ("Tempo total", "s"),
    "tempo_usuario": ("Tempo usuário", "s"),
    "tempo_sistema": ("Tempo sistema", "s"),
    "tempo_cpu": ("Tempo CPU", "s"),
    "utilizacao_cpu": ("Utilização CPU", "%"),
    "pico_memoria_kib": ("Pico de memória", "KiB"),
}
ENTRADA = "resultados.csv"
ENTRADA_BRUTOS = "merged.csv"
AMBIENTES = ["nativo", "docker", "vm"]
VARIANTES = ["rw_lento", "rw_rapido", "sort_lento", "sort_rapido"]
CORES = {"nativo": "#4C72B0", "docker": "#55A868", "vm": "#C44E52"}
# Codificação secundária (além da cor), para quem tem daltonismo / impressão P&B:
# verde e vermelho ficam parecidos para deuteranopia.
MARCADORES = {"nativo": "o", "docker": "s", "vm": "^"}
HACHURAS = {"nativo": "", "docker": "", "vm": "//"}
# Barra = média sem outliers; barrinha de erro = desvio padrão amostral
COL_VALOR = "media"
COL_ERRO = "desvio"


# --------------------------------------------------------------------------
# Utilitários
# --------------------------------------------------------------------------
def carregar_resumo(entrada):
    """Lê o resultados.csv mantendo N como texto ("1e3") e uma coluna numérica."""
    res = pd.read_csv(entrada, dtype={"N": str})
    res["N_num"] = res["N"].astype(float)
    return res


def carregar_brutos(entrada):
    """Lê o merged.csv; converte utilizacao_cpu de '99%' para 99.0."""
    df = pd.read_csv(entrada, dtype={"N": str})
    df["utilizacao_cpu"] = df["utilizacao_cpu"].astype(str).str.rstrip("%").astype(float)
    df["N_num"] = df["N"].astype(float)
    return df


def ns_ordenados(df, n_min=0):
    """Lista de N (como texto) em ordem numérica, só os >= n_min."""
    ns = df[["N", "N_num"]].drop_duplicates().sort_values("N_num")
    return ns.loc[ns["N_num"] >= n_min, "N"].tolist()


def tabela(res, metrica, col):
    """Pivot (N, variante) x ambiente com a coluna pedida, para uma métrica."""
    d = res[res["metrica"] == metrica]
    return d.pivot_table(index=["N", "variante"], columns="ambiente", values=col)


def overhead_pct(res, metrica, ambiente, referencia, col_valor, col_erro):
    """
    Overhead percentual de `ambiente` em relação a `referencia`:
        100 * (média_amb / média_ref - 1)
    Erro propagado (aproximação de primeira ordem da razão):
        100 * razão * sqrt((σa/μa)² + (σr/μr)²)
    Retorna NaN onde a média de referência é 0 (razão indefinida).
    """
    mu = tabela(res, metrica, col_valor)
    sd = tabela(res, metrica, col_erro)
    mu_a, mu_r = mu[ambiente], mu[referencia]
    sd_a, sd_r = sd[ambiente], sd[referencia]
    valido = (mu_r > 0) & (mu_a > 0)
    razao = (mu_a / mu_r).where(valido)
    erro = razao * np.sqrt((sd_a / mu_a) ** 2 + (sd_r / mu_r) ** 2)
    return 100 * (razao - 1), 100 * erro


def _estilo_eixo(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#dddddd", linewidth=0.6)
    ax.set_axisbelow(True)


# --------------------------------------------------------------------------
# 1) Gráfico original: colunas por (N, variante)
# --------------------------------------------------------------------------
def colunas(ENTRADA, metricas, ambientes, col_valor, col_erro):
    """Gera gráficos de barras para cada métrica, com média ± desvio padrão."""
    PASTA_SAIDA = Path("graficos_colunas")
    PASTA_SAIDA.mkdir(exist_ok=True)
    res = pd.read_csv(ENTRADA, dtype={"N": str})
    res["N_num"] = res["N"].astype(float)

    for (_, n, variante), grupo in res.groupby(["N_num", "N", "variante"], sort=True):
        fig, eixos = plt.subplots(1, len(metricas), figsize=(16, 4))

        for ax, (metrica, (titulo, unidade)) in zip(eixos, metricas.items()):
            d = grupo[grupo["metrica"] == metrica].set_index("ambiente").loc[ambientes]
            valores = d[col_valor].to_numpy()
            erros = d[col_erro].to_numpy()

            barras = ax.bar(
                ambientes, valores, yerr=erros, capsize=4,
                color=[CORES[a] for a in ambientes],
            )
            ax.bar_label(barras, fmt="%.3g", padding=3, fontsize=8)

            topo = (valores + erros).max()
            ax.set_ylim(0, topo * 1.15 if topo > 0 else 1)
            ax.set_title(titulo, fontsize=10)
            ax.set_ylabel(unidade)
            ax.tick_params(axis="x", labelsize=8)
            ax.spines[["top", "right"]].set_visible(False)

        fig.suptitle(f"N = {n}  |  {variante}   (média ± desvio padrão, sem outliers)")
        fig.tight_layout()
        fig.savefig(PASTA_SAIDA / f"colunas_N{n}_{variante}.png", dpi=150)
        plt.close(fig)
    print(f"{len(list(PASTA_SAIDA.glob('colunas_*.png')))} gráficos gravados em {PASTA_SAIDA}/")

# --------------------------------------------------------------------------
# 2) Overhead relativo ao nativo (barras agrupadas)
# --------------------------------------------------------------------------
def overhead_relativo(entrada, metricas, ambientes, variantes, col_valor, col_erro,
                      referencia="nativo", n_min=1e6):
    """
    Uma figura por métrica: para cada N >= n_min, um painel com o overhead (%)
    de cada ambiente em relação à `referencia`, por variante.
    Valor positivo = mais lento / usa mais que o nativo.
    """
    pasta = Path("graficos_overhead")
    pasta.mkdir(exist_ok=True)
    res = carregar_resumo(entrada)
    outros = [a for a in ambientes if a != referencia]
    ns = ns_ordenados(res, n_min)
    largura = 0.8 / len(outros)
    x = np.arange(len(variantes))

    for metrica in metricas:
        titulo, unidade = METRICAS[metrica]
        fig, eixos = plt.subplots(1, len(ns), figsize=(3.6 * len(ns) + 1, 4.2),
                                  sharey=True, squeeze=False)
        eixos = eixos[0]

        for ax, n in zip(eixos, ns):
            for i, amb in enumerate(outros):
                ov, err = overhead_pct(res, metrica, amb, referencia, col_valor, col_erro)
                v = ov.loc[n].reindex(variantes).to_numpy()
                e = err.loc[n].reindex(variantes).to_numpy()
                barras = ax.bar(
                    x + (i - (len(outros) - 1) / 2) * largura, v, largura * 0.92,
                    yerr=e, capsize=3, color=CORES[amb], hatch=HACHURAS[amb],
                    edgecolor="white", linewidth=0, label=amb,
                )
                ax.bar_label(barras, labels=[f"{val:+.1f}%" if np.isfinite(val) else "n/d"
                                             for val in v],
                             padding=3, fontsize=7)
            ax.axhline(0, color="#333333", linewidth=0.8)
            ax.margins(y=0.12)  # espaço para os rótulos acima/abaixo das barras
            ax.set_xticks(x, variantes, rotation=20, fontsize=8)
            ax.set_title(f"N = {n}", fontsize=10)
            _estilo_eixo(ax)
        eixos[0].set_ylabel(f"overhead vs {referencia} (%)")
        eixos[-1].legend(fontsize=8, frameon=False)

        fig.suptitle(f"Overhead de {titulo.lower()} em relação ao {referencia}")
        fig.tight_layout()
        fig.savefig(pasta / f"overhead_{metrica}.png", dpi=150)
        plt.close(fig)
    print(f"{len(metricas)} gráficos gravados em {pasta}/")


# --------------------------------------------------------------------------
# 3) Heatmap do overhead: variante x N, um painel por ambiente
# --------------------------------------------------------------------------
def heatmap_overhead(entrada, metricas, ambientes, variantes, col_valor, col_erro,
                     referencia="nativo", n_min=1e5):
    """
    Visão geral do overhead (%) vs `referencia` em todas as combinações
    variante × N. Escala divergente centrada em 0 (branco = igual ao nativo,
    vermelho = pior, azul = melhor). Células cinzas = sem dado (média 0).
    """
    pasta = Path("graficos_heatmap")
    pasta.mkdir(exist_ok=True)
    res = carregar_resumo(entrada)
    outros = [a for a in ambientes if a != referencia]
    ns = ns_ordenados(res, n_min)

    for metrica in metricas:
        titulo, _ = METRICAS[metrica]
        matrizes = {}
        for amb in outros:
            ov, _ = overhead_pct(res, metrica, amb, referencia, col_valor, col_erro)
            matrizes[amb] = ov.unstack("N").reindex(index=variantes, columns=ns)

        lim = np.nanmax([np.nanmax(np.abs(m.to_numpy())) for m in matrizes.values()])
        lim = lim if np.isfinite(lim) and lim > 0 else 1
        norma = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)

        fig, eixos = plt.subplots(1, len(outros), figsize=(1.3 * len(ns) * len(outros) + 2.5, 3.8),
                                  squeeze=False, layout="constrained")
        eixos = eixos[0]
        for ax, amb in zip(eixos, outros):
            m = matrizes[amb].to_numpy()
            ax.set_facecolor("#e6e6e6")  # NaN aparece cinza
            im = ax.imshow(m, cmap="RdBu_r", norm=norma, aspect="auto")
            for (i, j), val in np.ndenumerate(m):
                txt = "n/d" if np.isnan(val) else f"{val:+.1f}%"
                cor = "white" if np.isfinite(val) and abs(val) > 0.6 * lim else "#222222"
                ax.text(j, i, txt, ha="center", va="center", fontsize=8, color=cor)
            ax.set_xticks(range(len(ns)), [f"N={n}" for n in ns], fontsize=8)
            ax.set_yticks(range(len(variantes)), variantes, fontsize=8)
            ax.set_title(f"{amb} vs {referencia}", fontsize=10)
            ax.tick_params(length=0)
            for s in ax.spines.values():
                s.set_visible(False)
        fig.colorbar(im, ax=list(eixos), label="overhead (%)", shrink=0.9)
        fig.suptitle(f"Overhead de {titulo.lower()} em relação ao {referencia}")
        fig.savefig(pasta / f"heatmap_{metrica}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"{len(metricas)} gráficos gravados em {pasta}/")


# --------------------------------------------------------------------------
# 4) Distribuição dos dados brutos (boxplot + pontos), a partir do merged.csv
# --------------------------------------------------------------------------
def distribuicao_bruta(entrada_brutos, metricas, ambientes, ns=None):
    """
    Mesmo layout do gráfico de colunas (uma figura por N × variante, um painel
    por métrica), mas mostrando as 30 execuções: caixa = quartis, linha = mediana,
    pontos = cada execução (inclusive outliers, que a média do outro gráfico remove).
    `ns`: lista de N (texto) a incluir; None = todos.
    """
    pasta = Path("graficos_distribuicao")
    pasta.mkdir(exist_ok=True)
    df = carregar_brutos(entrada_brutos)
    if ns is not None:
        df = df[df["N"].isin(ns)]
    rng = np.random.default_rng(0)
    total = 0

    for (_, n, variante), grupo in df.groupby(["N_num", "N", "variante"], sort=True):
        fig, eixos = plt.subplots(1, len(metricas), figsize=(16, 4))
        for ax, (metrica, (titulo, unidade)) in zip(eixos, metricas.items()):
            dados = [grupo.loc[grupo["ambiente"] == a, metrica].to_numpy() for a in ambientes]
            caixas = ax.boxplot(dados, widths=0.55, showfliers=False, patch_artist=True,
                                medianprops=dict(color="#222222", linewidth=1.5))
            for caixa, amb in zip(caixas["boxes"], ambientes):
                caixa.set(facecolor=CORES[amb], alpha=0.35, edgecolor=CORES[amb])
            for i, (vals, amb) in enumerate(zip(dados, ambientes), start=1):
                jitter = rng.uniform(-0.15, 0.15, len(vals))
                ax.scatter(np.full(len(vals), i) + jitter, vals, s=10, color=CORES[amb],
                           marker=MARCADORES[amb], alpha=0.8, linewidths=0, zorder=3)
            ax.set_xticks(range(1, len(ambientes) + 1), ambientes, fontsize=8)
            ax.set_title(titulo, fontsize=10)
            ax.set_ylabel(unidade)
            _estilo_eixo(ax)
        fig.suptitle(f"N = {n}  |  {variante}   (distribuição das execuções brutas, com outliers)")
        fig.tight_layout()
        fig.savefig(pasta / f"distribuicao_N{n}_{variante}.png", dpi=150)
        plt.close(fig)
        total += 1
    print(f"{total} gráficos gravados em {pasta}/")

if __name__ == "__main__":
    colunas(ENTRADA, METRICAS, AMBIENTES, COL_VALOR, COL_ERRO)

    overhead_relativo(ENTRADA, METRICAS, AMBIENTES, VARIANTES, COL_VALOR, COL_ERRO, n_min=1e6)

    heatmap_overhead(ENTRADA, METRICAS, AMBIENTES, VARIANTES, COL_VALOR, COL_ERRO, n_min=1e6)

    distribuicao_bruta(ENTRADA_BRUTOS, METRICAS, AMBIENTES, ns=["1e6", "1e7"])