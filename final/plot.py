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
# 2) Escalabilidade: métrica x N (log-log), um painel por variante
# --------------------------------------------------------------------------
def escalabilidade(entrada, metricas, ambientes, variantes, col_valor, col_erro,
                   resolucao=0.01):
    """
    Uma figura por métrica: linhas (uma por ambiente) da média ± desvio em
    função de N, em escala log-log, com um painel por variante.
    Para métricas de tempo, pontos com média < `resolucao` (0,01 s, resolução
    do medidor) são omitidos: são 0 ou fruto de 1 execução isolada que marcou
    0,01 s, e não representam o tempo real. Memória não tem esse corte.
    """
    pasta = Path("graficos_escalabilidade")
    pasta.mkdir(exist_ok=True)
    res = carregar_resumo(entrada)

    for metrica in metricas:
        titulo, unidade = METRICAS[metrica]
        fig, eixos = plt.subplots(1, len(variantes), figsize=(16, 4.2), sharey=True)
        omitidos = False

        for ax, variante in zip(eixos, variantes):
            d = res[(res["metrica"] == metrica) & (res["variante"] == variante)]
            for amb in ambientes:
                da = d[d["ambiente"] == amb].sort_values("N_num")
                limiar = resolucao if unidade == "s" else 0
                da = da[da[col_valor] > 0]          # log não aceita 0
                da = da[da[col_valor] >= limiar]
                omitidos |= len(da) < d["N"].nunique()
                x, y, e = da["N_num"], da[col_valor], da[col_erro]
                # erro inferior limitado para não cruzar o 0 no log
                e_inf = np.minimum(e, y * 0.999)
                ax.errorbar(
                    x, y, yerr=[e_inf, e], label=amb, color=CORES[amb],
                    marker=MARCADORES[amb], markersize=6, linewidth=2, capsize=3,
                )
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title(variante, fontsize=10)
            ax.set_xlabel("N (tamanho da entrada)")
            _estilo_eixo(ax)
        eixos[0].set_ylabel(f"{titulo} ({unidade})")
        eixos[-1].legend(title="ambiente", fontsize=8, frameon=False)

        nota = (f"\npontos com média < {resolucao} s (resolução da medição) omitidos"
                if omitidos and unidade == "s" else "")
        fig.suptitle(f"{titulo} vs N   (média ± desvio padrão, sem outliers){nota}")
        fig.tight_layout()
        fig.savefig(pasta / f"escalabilidade_{metrica}.png", dpi=150)
        plt.close(fig)
    print(f"{len(metricas)} gráficos gravados em {pasta}/")


# --------------------------------------------------------------------------
# 3) Overhead relativo ao nativo (barras agrupadas)
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

        fig.suptitle(f"Overhead de {titulo.lower()} em relação ao {referencia}   "
                     f"(100·(média_amb/média_{referencia} − 1), erro propagado)")
        fig.tight_layout()
        fig.savefig(pasta / f"overhead_{metrica}.png", dpi=150)
        plt.close(fig)
    print(f"{len(metricas)} gráficos gravados em {pasta}/")


# --------------------------------------------------------------------------
# 4) Heatmap do overhead: variante x N, um painel por ambiente
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
# 5) Distribuição dos dados brutos (boxplot + pontos), a partir do merged.csv
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


# --------------------------------------------------------------------------
# 6) Decomposição do tempo: usuário + sistema (empilhado) vs tempo total
# --------------------------------------------------------------------------
def decomposicao_tempo(entrada, ambientes, variantes, col_valor, ns=("1e6", "1e7")):
    """
    Uma figura por N: em cada painel (variante), barras empilhadas com tempo de
    usuário (sólido) + tempo de sistema (claro, hachurado) por ambiente, e um
    traço preto no tempo total (relógio de parede). A distância entre o topo da
    barra e o traço é tempo em que o processo esperou (não estava na CPU).
    """
    pasta = Path("graficos_decomposicao")
    pasta.mkdir(exist_ok=True)
    res = carregar_resumo(entrada)

    for n in ns:
        fig, eixos = plt.subplots(1, len(variantes), figsize=(14, 4.2), sharey=True)
        for ax, variante in zip(eixos, variantes):
            d = res[(res["N"] == n) & (res["variante"] == variante)]
            m = d.pivot(index="ambiente", columns="metrica", values=col_valor).loc[ambientes]
            x = np.arange(len(ambientes))
            cores = [CORES[a] for a in ambientes]
            ax.bar(x, m["tempo_usuario"], 0.6, color=cores, label="usuário")
            ax.bar(x, m["tempo_sistema"], 0.6, bottom=m["tempo_usuario"], color=cores,
                   alpha=0.45, hatch="///", edgecolor="white", linewidth=0, label="sistema")
            ax.hlines(m["tempo_total"], x - 0.38, x + 0.38, color="#222222", linewidth=2,
                      label="tempo total")
            for xi, (_, linha) in zip(x, m.iterrows()):
                ax.annotate(f"sis {linha['tempo_sistema']:.3f}s\ntot {linha['tempo_total']:.3f}s",
                            (xi, max(linha["tempo_total"], linha["tempo_cpu"])),
                            xytext=(0, 4), textcoords="offset points",
                            ha="center", fontsize=7)
            ax.set_xticks(x, ambientes, fontsize=8)
            ax.set_title(variante, fontsize=10)
            _estilo_eixo(ax)
        eixos[0].set_ylabel("tempo (s)")
        topo = eixos[0].get_ylim()[1]
        eixos[0].set_ylim(0, topo * 1.18)
        # legenda neutra (cinza), pois a cor das barras é o ambiente
        from matplotlib.patches import Patch
        from matplotlib.lines import Line2D
        eixos[-1].legend(handles=[
            Patch(facecolor="#888888", label="usuário"),
            Patch(facecolor="#888888", alpha=0.45, hatch="///", edgecolor="white", label="sistema"),
            Line2D([], [], color="#222222", linewidth=2, label="tempo total"),
        ], fontsize=8, frameon=False, loc="upper right")
        fig.suptitle(f"N = {n}  |  decomposição do tempo (médias sem outliers)")
        fig.tight_layout()
        fig.savefig(pasta / f"decomposicao_N{n}.png", dpi=150)
        plt.close(fig)
    print(f"{len(ns)} gráficos gravados em {pasta}/")


# --------------------------------------------------------------------------
# 7) Variabilidade: coeficiente de variação (desvio/média)
# --------------------------------------------------------------------------
def variabilidade(entrada, metricas, ambientes, variantes, col_valor, col_erro, n_min=1e6):
    """
    Coeficiente de variação (CV = 100·desvio/média) por ambiente: mede a
    estabilidade/previsibilidade de cada ambiente, independente da escala.
    Use col_valor="media_bruta", col_erro="desvio_bruto" para ver a variação
    COM outliers (que é justamente onde ambientes instáveis aparecem).
    """
    pasta = Path("graficos_variabilidade")
    pasta.mkdir(exist_ok=True)
    res = carregar_resumo(entrada)
    ns = ns_ordenados(res, n_min)
    largura = 0.8 / len(ambientes)
    x = np.arange(len(variantes))
    sufixo = "bruto" if "bruto" in col_erro else "sem_outliers"

    for metrica in metricas:
        titulo, _ = METRICAS[metrica]
        mu = tabela(res, metrica, col_valor)
        sd = tabela(res, metrica, col_erro)
        cv = (100 * sd / mu).where(mu > 0)

        fig, eixos = plt.subplots(1, len(ns), figsize=(3.6 * len(ns) + 1, 4),
                                  sharey=True, squeeze=False)
        eixos = eixos[0]
        for ax, n in zip(eixos, ns):
            for i, amb in enumerate(ambientes):
                v = cv.loc[n, amb].reindex(variantes).to_numpy()
                barras = ax.bar(x + (i - (len(ambientes) - 1) / 2) * largura, v, largura * 0.92,
                                color=CORES[amb], hatch=HACHURAS[amb], edgecolor="white",
                                linewidth=0, label=amb)
                ax.bar_label(barras, fmt="%.1f", padding=2, fontsize=6)
            ax.set_xticks(x, variantes, rotation=20, fontsize=8)
            ax.set_title(f"N = {n}", fontsize=10)
            _estilo_eixo(ax)
        eixos[0].set_ylabel("coeficiente de variação (%)")
        eixos[-1].legend(fontsize=8, frameon=False)
        rotulo = "com outliers" if sufixo == "bruto" else "sem outliers"
        fig.suptitle(f"Variabilidade de {titulo.lower()}  (CV = desvio/média, {rotulo})")
        fig.tight_layout()
        fig.savefig(pasta / f"cv_{metrica}_{sufixo}.png", dpi=150)
        plt.close(fig)
    print(f"{len(metricas)} gráficos gravados em {pasta}/")


# ==========================================================================
# GRÁFICOS DE RADAR
# ==========================================================================
def _radar_base(ax, rotulos, rlim, rticks):
    """Configura um eixo polar: um raio por rótulo, começando no topo."""
    angulos = np.linspace(0, 2 * np.pi, len(rotulos), endpoint=False)
    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)
    ax.set_xticks(angulos, rotulos, fontsize=8)
    ax.tick_params(axis="x", pad=10)
    ax.set_ylim(*rlim)
    ax.set_yticks(rticks, [f"{t:g}" for t in rticks], fontsize=7, color="#666666")
    ax.set_rlabel_position(360 - 180 / len(rotulos))
    ax.grid(color="#cccccc", linewidth=0.6)
    ax.spines["polar"].set_color("#bbbbbb")
    return angulos


def _poligono(ax, angulos, valores, amb, preencher=True, tracejado=False):
    a = np.append(angulos, angulos[0])
    v = np.append(valores, valores[0])
    ax.plot(a, v, color=CORES[amb], linewidth=2, marker=MARCADORES[amb], markersize=5,
            linestyle="--" if tracejado else "-", label=amb)
    if preencher:
        ax.fill(a, v, color=CORES[amb], alpha=0.10)


def radar_metricas(entrada, metricas, ambientes, variantes, col_valor,
                   referencia="nativo", ns=("1e6", "1e7"), resolucao=0.01):
    """
    Uma figura por N, um radar por variante. Cada raio é uma métrica e o valor
    é a razão média_amb / média_referência: o nativo vira o círculo 1,0
    (tracejado) e o quanto o polígono de um ambiente sai para fora desse
    círculo mostra em quais métricas ele gasta mais.
    O eixo radial NÃO começa em 0 (as diferenças são de poucos %); a escala é
    a mesma em todos os painéis de uma figura.
    Métricas de tempo cuja média de referência fica abaixo de `resolucao`
    (0,01 s) são retiradas daquele N: a razão seria só ruído de medição.
    """
    pasta = Path("graficos_radar")
    pasta.mkdir(exist_ok=True)
    res = carregar_resumo(entrada)

    for n in ns:
        d = res[res["N"] == n]
        ref = d[d["ambiente"] == referencia].groupby("metrica")[col_valor].min()
        usadas = [m for m in metricas
                  if METRICAS[m][1] != "s" or ref.get(m, 0) >= resolucao]
        retiradas = [METRICAS[m][0] for m in metricas if m not in usadas]
        rotulos = [METRICAS[m][0] for m in usadas]
        razoes = {}
        for variante in variantes:
            dv = d[d["variante"] == variante].pivot(index="metrica", columns="ambiente",
                                                    values=col_valor).loc[usadas]
            razoes[variante] = dv[ambientes].div(dv[referencia], axis=0)
        todos = np.concatenate([r.to_numpy().ravel() for r in razoes.values()])
        todos = todos[np.isfinite(todos)]
        amplitude = max(todos.max(), 1) - min(todos.min(), 1)
        passo = next(p for p in (0.02, 0.05, 0.1, 0.2, 0.5, 1.0) if amplitude / p <= 5)
        lo = np.floor(min(todos.min(), 1) / passo) * passo - passo
        hi = np.ceil(max(todos.max(), 1) / passo) * passo
        ticks = np.round(np.arange(lo + passo, hi + passo / 2, passo), 2)

        fig, eixos = plt.subplots(1, len(variantes), figsize=(17, 4.8),
                                  subplot_kw={"projection": "polar"})
        for ax, variante in zip(eixos, variantes):
            angulos = _radar_base(ax, rotulos, (lo, hi), ticks)
            for amb in ambientes:
                _poligono(ax, angulos, razoes[variante][amb].to_numpy(), amb,
                          preencher=amb != referencia, tracejado=amb == referencia)
            ax.set_title(variante, fontsize=10, pad=18)
        eixos[-1].legend(loc="upper left", bbox_to_anchor=(1.12, 1.1), fontsize=8, frameon=False)
        nota = (f"\nretirado(s) por estar abaixo da resolução de {resolucao} s: "
                f"{', '.join(retiradas)}" if retiradas else "")
        fig.suptitle(f"N = {n}  |  razão em relação ao {referencia} por métrica "
                     f"(1,0 = igual ao {referencia}; para fora = gasta mais; "
                     f"eixo radial de {lo:.2f} a {hi:.2f}){nota}", fontsize=11)
        fig.tight_layout()
        fig.savefig(pasta / f"radar_metricas_N{n}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"{len(ns)} gráficos gravados em {pasta}/")


def radar_pontuacao(entrada, ambientes, variantes, ns=("1e6", "1e7"), resolucao=0.01):
    """
    Perfil de eficiência: cada raio é um critério em que MAIOR É MELHOR,
    pontuado de 0 a 1 como (melhor valor entre os ambientes) / (valor do ambiente).
    Assim o melhor ambiente em cada critério fica na borda (1,0).
      - Velocidade        : tempo total
      - CPU               : tempo de CPU (usuário + sistema)
      - Sistema           : tempo de sistema (custo de syscalls / virtualização)
      - Memória           : pico de memória
      - Estabilidade      : coeficiente de variação do tempo total (com outliers)
    Eixo radial de 0 a 1 (área maior = mais eficiente no geral).
    Critérios de tempo cuja média fica abaixo de `resolucao` (0,01 s) em algum
    ambiente são retirados daquele N (seriam só ruído de medição).
    """
    pasta = Path("graficos_radar")
    pasta.mkdir(exist_ok=True)
    res = carregar_resumo(entrada)
    criterios = {
        "Velocidade\n(tempo total)": ("tempo_total", "media"),
        "CPU\n(tempo CPU)": ("tempo_cpu", "media"),
        "Sistema\n(tempo sistema)": ("tempo_sistema", "media"),
        "Memória\n(pico)": ("pico_memoria_kib", "media"),
        "Estabilidade\n(1/CV)": ("tempo_total", "cv"),
    }

    for n in ns:
        d = res[res["N"] == n]
        minimos = d.groupby("metrica")["media"].min()
        usados = {r: c for r, c in criterios.items()
                  if METRICAS[c[0]][1] != "s" or minimos[c[0]] >= resolucao}
        retirados = [r.split("\n")[0] for r in criterios if r not in usados]
        fig, eixos = plt.subplots(1, len(variantes), figsize=(17, 4.8),
                                  subplot_kw={"projection": "polar"})
        for ax, variante in zip(eixos, variantes):
            dv = d[d["variante"] == variante].set_index(["metrica", "ambiente"])
            pont = {a: [] for a in ambientes}
            for metrica, tipo in usados.values():
                if tipo == "cv":
                    vals = {a: dv.loc[(metrica, a), "desvio_bruto"] / dv.loc[(metrica, a), "media_bruta"]
                            for a in ambientes}
                else:
                    vals = {a: dv.loc[(metrica, a), "media"] for a in ambientes}
                melhor = min(vals.values())
                for a in ambientes:
                    pont[a].append(melhor / vals[a] if vals[a] > 0 else np.nan)

            angulos = _radar_base(ax, list(usados), (0, 1.0), [0.25, 0.5, 0.75, 1.0])
            for amb in ambientes:
                _poligono(ax, angulos, np.array(pont[amb]), amb)
            ax.set_title(variante, fontsize=10, pad=22)
        eixos[-1].legend(loc="upper left", bbox_to_anchor=(1.15, 1.1), fontsize=8, frameon=False)
        nota = (f"\nretirado(s) por estar abaixo da resolução de {resolucao} s: "
                f"{', '.join(retirados)}" if retirados else "")
        fig.suptitle(f"N = {n}  |  perfil de eficiência (1,0 = melhor ambiente no critério; "
                     f"pontuação = melhor/valor){nota}", fontsize=11)
        fig.tight_layout()
        fig.savefig(pasta / f"radar_pontuacao_N{n}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"{len(ns)} gráficos gravados em {pasta}/")


# ==========================================================================
# GRÁFICOS DE DISPERSÃO (a partir dos dados brutos)
# ==========================================================================
def dispersao(entrada_brutos, metrica_x, metrica_y, ambientes, variantes,
              ns=("1e6", "1e7"), jitter=0.0):
    """
    Uma figura por N, um painel por variante: cada ponto é uma execução,
    x = metrica_x e y = metrica_y, cor/marcador = ambiente. O "x" grande é a
    média de cada ambiente. Mostra se os ambientes formam grupos separados e
    se as duas métricas andam juntas.
    `jitter`: deslocamento aleatório (em unidades da métrica) para desfazer a
    sobreposição de pontos quando a métrica é discreta (ex.: tempos com
    resolução de 0,01 s → use jitter=0.003). Aplicado só às métricas em segundos.
    """
    pasta = Path("graficos_dispersao")
    pasta.mkdir(exist_ok=True)
    df = carregar_brutos(entrada_brutos)
    rng = np.random.default_rng(0)
    tx, ux = METRICAS[metrica_x]
    ty, uy = METRICAS[metrica_y]

    for n in ns:
        d = df[df["N"] == n]
        fig, eixos = plt.subplots(1, len(variantes), figsize=(16, 4.2))
        for ax, variante in zip(eixos, variantes):
            dv = d[d["variante"] == variante]
            for amb in ambientes:
                da = dv[dv["ambiente"] == amb]
                x = da[metrica_x].to_numpy(dtype=float)
                y = da[metrica_y].to_numpy(dtype=float)
                if jitter:
                    if ux == "s":
                        x = x + rng.uniform(-jitter, jitter, len(x))
                    if uy == "s":
                        y = y + rng.uniform(-jitter, jitter, len(y))
                ax.scatter(x, y, s=22, color=CORES[amb], marker=MARCADORES[amb], alpha=0.7,
                           edgecolors="white", linewidths=0.4, label=amb, zorder=3)
                ax.scatter(da[metrica_x].mean(), da[metrica_y].mean(), s=120, marker="X",
                           color=CORES[amb], edgecolors="#222222", linewidths=1, zorder=4)
            ax.set_title(variante, fontsize=10)
            ax.set_xlabel(f"{tx} ({ux})", fontsize=9)
            ax.tick_params(labelsize=8)
            ax.grid(color="#e3e3e3", linewidth=0.6)
            ax.set_axisbelow(True)
            ax.spines[["top", "right"]].set_visible(False)
        eixos[0].set_ylabel(f"{ty} ({uy})", fontsize=9)
        eixos[-1].legend(fontsize=8, frameon=False, markerscale=1.2)
        nota = f"  (jitter ±{jitter} s nos tempos para separar pontos sobrepostos)" if jitter else ""
        fig.suptitle(f"N = {n}  |  {ty} × {tx} por execução  (X = média do ambiente){nota}",
                     fontsize=11)
        fig.tight_layout()
        fig.savefig(pasta / f"dispersao_{metrica_x}_x_{metrica_y}_N{n}.png", dpi=150)
        plt.close(fig)
    print(f"{len(ns)} gráficos gravados em {pasta}/")


def dispersao_pareada(entrada_brutos, metrica, ambientes, variantes,
                      referencia="nativo", ns=("1e6", "1e7"), jitter=0.0):
    """
    Comparação pareada por arquivo de entrada: cada ponto é um mesmo arquivo
    (ex.: in_1e7_12) executado no `referencia` (eixo x) e em outro ambiente
    (eixo y). A diagonal tracejada é y = x (desempenho igual).
    Pontos acima da diagonal = o ambiente foi mais lento que o nativo naquela
    mesma entrada. Isola o efeito do ambiente do efeito da entrada.
    `jitter`: deslocamento aleatório (s) para separar pontos sobrepostos quando
    os tempos caem na grade de 0,01 s (útil em N = 1e6). A porcentagem
    "acima" é calculada nos valores originais, sem jitter.
    """
    rng = np.random.default_rng(0)
    pasta = Path("graficos_dispersao")
    pasta.mkdir(exist_ok=True)
    df = carregar_brutos(entrada_brutos)
    outros = [a for a in ambientes if a != referencia]
    titulo, unidade = METRICAS[metrica]

    for n in ns:
        d = df[df["N"] == n]
        fig, eixos = plt.subplots(1, len(variantes), figsize=(16, 5))
        for ax, variante in zip(eixos, variantes):
            dv = d[d["variante"] == variante].pivot(index="arquivo", columns="ambiente",
                                                    values=metrica)
            vmin = dv[ambientes].min().min()
            vmax = dv[ambientes].max().max()
            folga = max((vmax - vmin) * 0.05, jitter * 1.5, 0.005)
            lim = (vmin - folga, vmax + folga)
            ax.plot(lim, lim, color="#555555", linestyle="--", linewidth=1, label="y = x")
            for amb in outros:
                acima = (dv[amb] > dv[referencia]).mean() * 100
                jx = rng.uniform(-jitter, jitter, len(dv)) if jitter else 0
                jy = rng.uniform(-jitter, jitter, len(dv)) if jitter else 0
                ax.scatter(dv[referencia] + jx, dv[amb] + jy, s=24, color=CORES[amb],
                           marker=MARCADORES[amb], alpha=0.75, edgecolors="white",
                           linewidths=0.4, zorder=3,
                           label=f"{amb} ({acima:.0f}% acima)")
            ax.set_xlim(lim)
            ax.set_ylim(lim)
            ax.set_aspect("equal")
            ax.set_title(variante, fontsize=10)
            ax.set_xlabel(f"{referencia} ({unidade})", fontsize=9)
            ax.tick_params(labelsize=8)
            ax.grid(color="#e3e3e3", linewidth=0.6)
            ax.set_axisbelow(True)
            ax.spines[["top", "right"]].set_visible(False)
            ax.legend(fontsize=7, frameon=False, loc="lower right")
        eixos[0].set_ylabel(f"outro ambiente ({unidade})", fontsize=9)
        fig.suptitle(f"N = {n}  |  {titulo}: mesmo arquivo de entrada, {referencia} × outro ambiente "
                     f"(acima da diagonal = mais lento que o {referencia})"
                     + (f"\njitter ±{jitter} s para separar pontos sobrepostos" if jitter else ""),
                     fontsize=11)
        fig.tight_layout()
        fig.savefig(pasta / f"pareada_{metrica}_N{n}.png", dpi=150, bbox_inches="tight")
        plt.close(fig)
    print(f"{len(ns)} gráficos gravados em {pasta}/")


if __name__ == "__main__":
    colunas(ENTRADA, METRICAS, AMBIENTES, COL_VALOR, COL_ERRO)

    escalabilidade(ENTRADA, ["tempo_total", "tempo_cpu", "pico_memoria_kib"],
                   AMBIENTES, VARIANTES, COL_VALOR, COL_ERRO)

    # Tempos: só N >= 1e6 (abaixo disso a resolução de 0,01 s domina)
    overhead_relativo(ENTRADA, ["tempo_total", "tempo_cpu", "tempo_sistema"],
                      AMBIENTES, VARIANTES, COL_VALOR, COL_ERRO, n_min=1e6)
    # Memória: todos os N têm valor
    overhead_relativo(ENTRADA, ["pico_memoria_kib"],
                      AMBIENTES, VARIANTES, COL_VALOR, COL_ERRO, n_min=0)

    heatmap_overhead(ENTRADA, ["tempo_total"], AMBIENTES, VARIANTES, COL_VALOR, COL_ERRO, n_min=1e6)
    heatmap_overhead(ENTRADA, ["pico_memoria_kib"], AMBIENTES, VARIANTES, COL_VALOR, COL_ERRO, n_min=0)

    distribuicao_bruta(ENTRADA_BRUTOS, METRICAS, AMBIENTES, ns=["1e6", "1e7"])

    decomposicao_tempo(ENTRADA, AMBIENTES, VARIANTES, COL_VALOR, ns=["1e6", "1e7"])

    variabilidade(ENTRADA, ["tempo_total"], AMBIENTES, VARIANTES,
                  "media_bruta", "desvio_bruto", n_min=1e6)

    # ---- Radar ----
    radar_metricas(ENTRADA, ["tempo_total", "tempo_usuario", "tempo_sistema",
                             "tempo_cpu", "pico_memoria_kib"],
                   AMBIENTES, VARIANTES, COL_VALOR, ns=["1e6", "1e7"])
    radar_pontuacao(ENTRADA, AMBIENTES, VARIANTES, ns=["1e6", "1e7"])

    # ---- Dispersão ----
    dispersao(ENTRADA_BRUTOS, "tempo_total", "pico_memoria_kib", AMBIENTES, VARIANTES,
              ns=["1e6", "1e7"])
    dispersao(ENTRADA_BRUTOS, "tempo_usuario", "tempo_sistema", AMBIENTES, VARIANTES,
              ns=["1e6", "1e7"], jitter=0.003)
    dispersao_pareada(ENTRADA_BRUTOS, "tempo_total", AMBIENTES, VARIANTES, ns=["1e6"], jitter=0.003)
    dispersao_pareada(ENTRADA_BRUTOS, "tempo_total", AMBIENTES, VARIANTES, ns=["1e7"])