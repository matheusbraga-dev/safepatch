"""Exportador de relatório de comparação em formato Markdown (GFM)."""

from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from safepatch.domain.modelos import RelatorioComparacao
from safepatch.domain.protocolos import ProtocoloDiferenciador, ProtocoloExportador
from safepatch.infrastructure.diff.motor_diff import MotorDiff
from safepatch.infrastructure.sistema_arquivos.escritor_atomico import escrever_arquivo_atomico

CaminhoPath = Union[str, Path]


class ExportadorMarkdown(ProtocoloExportador):
    """Exporta o relatório em formato Markdown (GitHub Flavored Markdown)."""

    def __init__(self, diferenciador: Optional[ProtocoloDiferenciador] = None):
        self.diferenciador = diferenciador

    def para_markdown(
        self,
        relatorio: RelatorioComparacao,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
    ) -> str:
        """Gera o texto em Markdown estruturado com tabelas e diffs."""
        diff_motor = self.diferenciador or (MotorDiff() if incluir_diff else None)
        linhas = [
            "# Relatório de Comparação de Pacotes\n",
            f"**Data da Análise:** {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n",
            f"- **Pacote Base:** `{relatorio.pacote_base}`",
            f"- **Pacote Alvo:** `{relatorio.pacote_alvo}`\n",
            "## Resumo Estatístico\n",
            "| Categoria | Quantidade |",
            "| :--- | :--- |",
            f"| **Adicionados** | {relatorio.total_adicionados} |",
            f"| **Removidos** | {relatorio.total_removidos} |",
            f"| **Modificados (Conflitos)** | {relatorio.total_modificados} |",
            f"| **Inalterados** | {relatorio.total_inalterados} |",
        ]

        if relatorio.ignorados:
            linhas.append(f"| **Ignorados** | {relatorio.total_ignorados} |")
        linhas.append("\n---\n")

        # 1. Modificados
        if relatorio.modificados:
            linhas.append("## [~] Arquivos Modificados (Atenção / Conflitos)\n")
            linhas.append(
                "| Arquivo | Tamanho Anterior | Novo Tamanho | Variação | SHA-256 Base | SHA-256 Alvo |"
            )
            linhas.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for m in relatorio.modificados:
                h_base = f"`{m.base.hash_sha256[:8]}...`"
                h_alvo = f"`{m.alvo.hash_sha256[:8]}...`"
                delta_txt = "Bytecode ↔ Fonte" if m.comparando_fonte_com_bytecode else m.delta_formatado
                caminho_md = f"`{m.caminho}`"
                if m.alvo.caminho_origem and m.alvo.caminho_origem != m.caminho:
                    caminho_md += f"<br><sub>Fonte: `{m.alvo.caminho_origem}`</sub>"
                linhas.append(
                    f"| {caminho_md} | {m.base.tamanho_formatado} | {m.alvo.tamanho_formatado} | {delta_txt} | {h_base} | {h_alvo} |"
                )
            linhas.append("")

            if incluir_diff and diff_motor and caminho_base and caminho_alvo:
                linhas.append("### Detalhes das Alterações (Diff Estilo Git)\n")
                for m in relatorio.modificados:
                    diff_linhas = "".join(
                        diff_motor.diff_modificado(caminho_base, caminho_alvo, m.caminho)
                    )
                    linhas.append(
                        f"<details><summary><b>Diff:</b> <code>{m.caminho}</code></summary>\n"
                    )
                    linhas.append("```diff")
                    linhas.append(diff_linhas.strip())
                    linhas.append("```\n</details>\n")

        # 2. Adicionados
        if relatorio.adicionados:
            linhas.append("## [+] Arquivos Adicionados\n")
            linhas.append("| Arquivo | Tamanho | SHA-256 |")
            linhas.append("| :--- | :--- | :--- |")
            for a in relatorio.adicionados:
                linhas.append(f"| `{a.caminho}` | {a.tamanho_formatado} | `{a.hash_sha256[:8]}...` |")
            linhas.append("")

            if incluir_diff and diff_motor and caminho_alvo:
                linhas.append("### Conteúdo dos Arquivos Adicionados\n")
                for a in relatorio.adicionados:
                    diff_linhas = "".join(diff_motor.diff_adicionado(caminho_alvo, a.caminho))
                    linhas.append(
                        f"<details><summary><b>Novo:</b> <code>{a.caminho}</code></summary>\n"
                    )
                    linhas.append("```diff")
                    linhas.append(diff_linhas.strip())
                    linhas.append("```\n</details>\n")

        # 3. Removidos
        if relatorio.removidos:
            linhas.append("## [-] Arquivos Removidos\n")
            linhas.append("| Arquivo | Tamanho | SHA-256 |")
            linhas.append("| :--- | :--- | :--- |")
            for r in relatorio.removidos:
                linhas.append(f"| `{r.caminho}` | {r.tamanho_formatado} | `{r.hash_sha256[:8]}...` |")
            linhas.append("")

            if incluir_diff and diff_motor and caminho_base:
                linhas.append("### Conteúdo dos Arquivos Removidos\n")
                for r in relatorio.removidos:
                    diff_linhas = "".join(diff_motor.diff_removido(caminho_base, r.caminho))
                    linhas.append(
                        f"<details><summary><b>Removido:</b> <code>{r.caminho}</code></summary>\n"
                    )
                    linhas.append("```diff")
                    linhas.append(diff_linhas.strip())
                    linhas.append("```\n</details>\n")

        # 4. Ignorados
        if relatorio.ignorados:
            linhas.append("## [*] Arquivos Ignorados\n")
            for ig in relatorio.ignorados:
                linhas.append(f"- `{ig}`")
            linhas.append("")

        return "\n".join(linhas)

    def exportar(
        self,
        relatorio: RelatorioComparacao,
        caminho_arquivo: CaminhoPath,
        incluir_diff: bool = False,
        caminho_base: Optional[CaminhoPath] = None,
        caminho_alvo: Optional[CaminhoPath] = None,
    ) -> None:
        """Gera e grava o relatório em arquivo Markdown de forma atômica."""
        conteudo = self.para_markdown(
            relatorio,
            incluir_diff=incluir_diff,
            caminho_base=caminho_base,
            caminho_alvo=caminho_alvo,
        )
        escrever_arquivo_atomico(caminho_arquivo, conteudo)
