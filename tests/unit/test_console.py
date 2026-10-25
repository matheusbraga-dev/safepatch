"""Testes unitários para o renderizador de console (RenderizadorConsole)."""

import io
import unittest
from tests.helpers import SRC_PATH, criar_jar_temporario

from safepatch.domain.modelos import (
    ArquivoInfo,
    ArquivoModificadoInfo,
    RelatorioComparacao,
)
from safepatch.presentation.console import RenderizadorConsole


class TestRenderizadorConsole(unittest.TestCase):
    def test_relatorio_console_limite_e_verbose(self):
        adicionados = [ArquivoInfo(f"arq_{i}.txt", f"hash_{i}", 10) for i in range(15)]
        relatorio = RelatorioComparacao(
            pacote_base="base.jar",
            pacote_alvo="alvo.jar",
            adicionados=adicionados,
        )

        # Modo limitado
        saida_limitada = io.StringIO()
        gerador_limitado = RenderizadorConsole(
            usar_cores=False, limite=5, verbose=False, saida=saida_limitada
        )
        gerador_limitado.renderizar(relatorio)
        texto_limitado = saida_limitada.getvalue()
        self.assertIn("... e mais 10 arquivos adicionados (use --verbose para ver todos)", texto_limitado)

        # Modo verbose
        saida_verbose = io.StringIO()
        gerador_verbose = RenderizadorConsole(
            usar_cores=False, limite=5, verbose=True, saida=saida_verbose
        )
        gerador_verbose.renderizar(relatorio)
        texto_verbose = saida_verbose.getvalue()
        self.assertNotIn("... e mais", texto_verbose)
        self.assertIn("arq_14.txt", texto_verbose)

    def test_relatorio_console_com_diff(self):
        jar_base = criar_jar_temporario({"texto.txt": "versao 1\n"})
        jar_alvo = criar_jar_temporario({"texto.txt": "versao 2\n"})

        base_info = ArquivoInfo("texto.txt", "h_base", 9)
        alvo_info = ArquivoInfo("texto.txt", "h_alvo", 9)
        relatorio = RelatorioComparacao(
            pacote_base="base.jar",
            pacote_alvo="alvo.jar",
            modificados=[ArquivoModificadoInfo("texto.txt", base_info, alvo_info)],
        )

        saida = io.StringIO()
        gerador = RenderizadorConsole(
            usar_cores=False,
            mostrar_diff=True,
            caminho_base=jar_base,
            caminho_alvo=jar_alvo,
            saida=saida,
        )
        gerador.renderizar(relatorio)
        conteudo = saida.getvalue()

        self.assertIn("diff --git a/texto.txt b/texto.txt", conteudo)
        self.assertIn("-versao 1", conteudo)
        self.assertIn("+versao 2", conteudo)


if __name__ == "__main__":
    unittest.main()
