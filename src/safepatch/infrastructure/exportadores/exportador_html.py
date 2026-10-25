"""Exportador de relatório visual moderno em formato HTML5 com segurança contra XSS."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from safepatch.domain.modelos import RelatorioComparacao
from safepatch.domain.protocolos import ProtocoloDiferenciador, ProtocoloExportador
from safepatch.infrastructure.diff.motor_diff import MotorDiff
from safepatch.infrastructure.sistema_arquivos.escritor_atomico import escrever_arquivo_atomico
from safepatch.shared.sanitizacao import escapar_html, formatar_diff_html

CaminhoPath = Union[str, Path]


class ExportadorHTML(ProtocoloExportador):
    """Exporta o relatório em uma página HTML5 moderna, visualmente elegante e protegida contra XSS."""

    def __init__(self, diferenciador: Optional[ProtocoloDiferenciador] = None):
        self.diferenciador = diferenciador

    def para_html(
        self,
        relatorio: RelatorioComparacao,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
    ) -> str:
        """Gera o código HTML completo e sanitizado."""
        diff_motor = self.diferenciador or (MotorDiff() if incluir_diff else None)
        data_formatada = datetime.now().strftime("%d/%m/%Y às %H:%M:%S")

        nome_base_escapado = escapar_html(relatorio.pacote_base)
        nome_alvo_escapado = escapar_html(relatorio.pacote_alvo)

        # 1. Modificados
        modificados_html = ""
        for m in relatorio.modificados:
            caminho_escapado = escapar_html(m.caminho)
            sinal_classe = "badge-danger" if m.delta_bytes > 0 else "badge-info"
            diff_row = ""

            if incluir_diff and diff_motor and caminho_base and caminho_alvo:
                diff_linhas = diff_motor.diff_modificado(caminho_base, caminho_alvo, m.caminho)
                diff_formatado = formatar_diff_html(diff_linhas)
                diff_row = f"""
                <tr class="diff-row">
                    <td colspan="6">
                        <details class="diff-details">
                            <summary>Ver Diff Estilo Git</summary>
                            <div class="diff-container">{diff_formatado}</div>
                        </details>
                    </td>
                </tr>
                """

            modificados_html += f"""
            <tr class="data-row">
                <td class="col-file"><code title="{caminho_escapado}">{caminho_escapado}</code></td>
                <td>{m.base.tamanho_formatado}</td>
                <td>{m.alvo.tamanho_formatado}</td>
                <td><span class="badge {sinal_classe}">{m.delta_formatado}</span></td>
                <td><code title="{escapar_html(m.base.hash_sha256)}">{escapar_html(m.base.hash_sha256[:10])}...</code></td>
                <td><code title="{escapar_html(m.alvo.hash_sha256)}">{escapar_html(m.alvo.hash_sha256[:10])}...</code></td>
            </tr>
            {diff_row}
            """

        # 2. Adicionados
        adicionados_html = ""
        for a in relatorio.adicionados:
            caminho_escapado = escapar_html(a.caminho)
            diff_row = ""

            if incluir_diff and diff_motor and caminho_alvo:
                diff_linhas = diff_motor.diff_adicionado(caminho_alvo, a.caminho)
                diff_formatado = formatar_diff_html(diff_linhas)
                diff_row = f"""
                <tr class="diff-row">
                    <td colspan="3">
                        <details class="diff-details">
                            <summary>Ver Conteúdo Adicionado</summary>
                            <div class="diff-container">{diff_formatado}</div>
                        </details>
                    </td>
                </tr>
                """

            adicionados_html += f"""
            <tr class="data-row">
                <td class="col-file"><code title="{caminho_escapado}">{caminho_escapado}</code></td>
                <td>{a.tamanho_formatado}</td>
                <td><code title="{escapar_html(a.hash_sha256)}">{escapar_html(a.hash_sha256[:10])}...</code></td>
            </tr>
            {diff_row}
            """

        # 3. Removidos
        removidos_html = ""
        for r in relatorio.removidos:
            caminho_escapado = escapar_html(r.caminho)
            diff_row = ""

            if incluir_diff and diff_motor and caminho_base:
                diff_linhas = diff_motor.diff_removido(caminho_base, r.caminho)
                diff_formatado = formatar_diff_html(diff_linhas)
                diff_row = f"""
                <tr class="diff-row">
                    <td colspan="3">
                        <details class="diff-details">
                            <summary>Ver Conteúdo Removido</summary>
                            <div class="diff-container">{diff_formatado}</div>
                        </details>
                    </td>
                </tr>
                """

            removidos_html += f"""
            <tr class="data-row">
                <td class="col-file"><code title="{caminho_escapado}">{caminho_escapado}</code></td>
                <td>{r.tamanho_formatado}</td>
                <td><code title="{escapar_html(r.hash_sha256)}">{escapar_html(r.hash_sha256[:10])}...</code></td>
            </tr>
            {diff_row}
            """

        secao_modificados = (
            f"""<section>
                <h2>[~] Arquivos Modificados (Atenção / Conflitos)</h2>
                <div class='table-responsive'>
                    <table>
                        <colgroup>
                            <col style='width: 38%;'><col style='width: 12%;'><col style='width: 12%;'>
                            <col style='width: 14%;'><col style='width: 12%;'><col style='width: 12%;'>
                        </colgroup>
                        <thead>
                            <tr>
                                <th>Arquivo</th><th>Tamanho Base</th><th>Tamanho Alvo</th>
                                <th>Variação</th><th>SHA-256 Base</th><th>SHA-256 Alvo</th>
                            </tr>
                        </thead>
                        <tbody>{modificados_html}</tbody>
                    </table>
                </div>
            </section>"""
            if relatorio.modificados
            else ""
        )

        secao_adicionados = (
            f"""<section>
                <h2>[+] Arquivos Adicionados</h2>
                <div class='table-responsive'>
                    <table>
                        <colgroup><col style='width: 60%;'><col style='width: 15%;'><col style='width: 25%;'></colgroup>
                        <thead><tr><th>Arquivo</th><th>Tamanho</th><th>SHA-256</th></tr></thead>
                        <tbody>{adicionados_html}</tbody>
                    </table>
                </div>
            </section>"""
            if relatorio.adicionados
            else ""
        )

        secao_removidos = (
            f"""<section>
                <h2>[-] Arquivos Removidos</h2>
                <div class='table-responsive'>
                    <table>
                        <colgroup><col style='width: 60%;'><col style='width: 15%;'><col style='width: 25%;'></colgroup>
                        <thead><tr><th>Arquivo</th><th>Tamanho</th><th>SHA-256</th></tr></thead>
                        <tbody>{removidos_html}</tbody>
                    </table>
                </div>
            </section>"""
            if relatorio.removidos
            else ""
        )

        return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório de Comparação - {nome_alvo_escapado}</title>
    <style>
        :root {{
            --bg: #0b1120;
            --surface: #1e293b;
            --surface-hover: #243247;
            --border: #334155;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --primary: #38bdf8;
            --success: #4ade80;
            --warning: #facc15;
            --danger: #f87171;
            --info: #818cf8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            line-height: 1.5;
            padding: 2rem;
        }}
        .container {{ max-width: 1300px; margin: 0 auto; }}
        header {{
            background: var(--surface);
            padding: 1.5rem 2rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
        }}
        h1 {{ font-size: 1.75rem; color: var(--primary); margin-bottom: 0.5rem; }}
        .meta {{ color: var(--text-muted); font-size: 0.9rem; }}
        .meta p {{ margin-bottom: 0.25rem; }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .card {{
            background: var(--surface);
            padding: 1.25rem;
            border-radius: 10px;
            border: 1px solid var(--border);
            text-align: center;
        }}
        .card .number {{ font-size: 2rem; font-weight: bold; margin-bottom: 0.25rem; }}
        .card .label {{ font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); }}
        .card.modificados .number {{ color: var(--warning); }}
        .card.adicionados .number {{ color: var(--success); }}
        .card.removidos .number {{ color: var(--danger); }}
        .card.inalterados .number {{ color: var(--info); }}
        section {{
            background: var(--surface);
            padding: 1.5rem;
            border-radius: 12px;
            border: 1px solid var(--border);
            margin-bottom: 1.5rem;
            overflow: hidden;
        }}
        h2 {{ font-size: 1.25rem; margin-bottom: 1.2rem; display: flex; align-items: center; gap: 0.5rem; }}
        .table-responsive {{ width: 100%; overflow-x: auto; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.88rem;
            table-layout: fixed;
        }}
        th, td {{
            text-align: left;
            padding: 0.75rem 1rem;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        th {{
            background: rgba(255,255,255,0.03);
            color: var(--text-muted);
            font-weight: 600;
        }}
        .col-file {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
        code {{
            font-family: Consolas, Monaco, "Courier New", monospace;
            background: rgba(0,0,0,0.35);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.85em;
            word-break: break-all;
        }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-danger {{ background: rgba(248, 113, 113, 0.2); color: var(--danger); }}
        .badge-info {{ background: rgba(56, 189, 248, 0.2); color: var(--primary); }}
        .diff-row td {{
            padding: 0 1rem 1rem 1rem !important;
            border-bottom: 2px solid var(--border);
            background: rgba(11, 17, 32, 0.4);
        }}
        .diff-details {{ width: 100%; margin-top: 0.5rem; }}
        .diff-details summary {{
            cursor: pointer;
            color: var(--primary);
            font-weight: 600;
            padding: 0.4rem 0.8rem;
            background: rgba(56, 189, 248, 0.08);
            border-radius: 6px;
            border: 1px solid rgba(56, 189, 248, 0.25);
            outline: none;
            display: inline-block;
            user-select: none;
            transition: all 0.2s ease;
            font-size: 0.82rem;
        }}
        .diff-details summary:hover {{
            background: rgba(56, 189, 248, 0.18);
            border-color: var(--primary);
        }}
        .diff-container {{
            background: #060913;
            border: 1px solid #334155;
            border-radius: 8px;
            margin-top: 0.6rem;
            padding: 0.5rem 0;
            font-family: Consolas, Monaco, "Courier New", monospace;
            font-size: 0.82rem;
            line-height: 1.45;
            overflow-x: auto;
            max-width: 100%;
            box-shadow: inset 0 2px 4px rgba(0, 0, 0, 0.5);
        }}
        .diff-line {{
            padding: 0.12rem 1rem;
            white-space: pre;
            font-family: Consolas, Monaco, "Courier New", monospace;
        }}
        .diff-line.diff-add {{
            color: #4ade80;
            background-color: rgba(74, 222, 128, 0.12);
            border-left: 3px solid #4ade80;
        }}
        .diff-line.diff-del {{
            color: #f87171;
            background-color: rgba(248, 113, 113, 0.12);
            border-left: 3px solid #f87171;
        }}
        .diff-line.diff-hunk {{
            color: #38bdf8;
            background-color: rgba(56, 189, 248, 0.08);
            font-weight: 600;
        }}
        .diff-line.diff-meta {{ color: #94a3b8; font-weight: 600; }}
        .diff-line.diff-ctx {{ color: #cbd5e1; }}
        .footer {{
            text-align: center;
            margin-top: 3rem;
            padding: 1.5rem 0;
            color: var(--text-muted);
            font-size: 0.9rem;
            border-top: 1px solid var(--border);
        }}
        .footer a {{ color: var(--primary); text-decoration: none; font-weight: 500; }}
        .footer a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Relatório de Comparação de Pacotes</h1>
            <div class="meta">
                <p><strong>Base:</strong> <code>{nome_base_escapado}</code> &nbsp;|&nbsp; <strong>Alvo:</strong> <code>{nome_alvo_escapado}</code></p>
                <p>Gerado em: {data_formatada}</p>
            </div>
        </header>

        <div class="grid">
            <div class="card modificados">
                <div class="number">{relatorio.total_modificados}</div>
                <div class="label">Modificados</div>
            </div>
            <div class="card adicionados">
                <div class="number">{relatorio.total_adicionados}</div>
                <div class="label">Adicionados</div>
            </div>
            <div class="card removidos">
                <div class="number">{relatorio.total_removidos}</div>
                <div class="label">Removidos</div>
            </div>
            <div class="card inalterados">
                <div class="number">{relatorio.total_inalterados}</div>
                <div class="label">Inalterados</div>
            </div>
        </div>

        {secao_modificados}
        {secao_adicionados}
        {secao_removidos}

        <div class="footer">
            Make With Coffee by <a href="https://matheusbraga.dev" target="_blank" rel="noopener noreferrer">matheusbraga.dev</a>
        </div>
    </div>
</body>
</html>
"""

    def exportar(
        self,
        relatorio: RelatorioComparacao,
        caminho_arquivo: CaminhoPath,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
    ) -> None:
        """Gera e grava o relatório em arquivo HTML de forma atômica."""
        conteudo = self.para_html(
            relatorio,
            incluir_diff=incluir_diff,
            caminho_base=caminho_base,
            caminho_alvo=caminho_alvo,
        )
        escrever_arquivo_atomico(caminho_arquivo, conteudo)
