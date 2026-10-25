"""Testes unitários para os exportadores (ExportadorJSON, ExportadorMarkdown, ExportadorHTML)."""

import json
import tempfile
import unittest
from pathlib import Path
from tests.helpers import SRC_PATH

from safepatch.domain.modelos import (
    ArquivoInfo,
    ArquivoModificadoInfo,
    RelatorioComparacao,
)
from safepatch.infrastructure.exportadores.exportador_html import ExportadorHTML
from safepatch.infrastructure.exportadores.exportador_json import ExportadorJSON
from safepatch.infrastructure.exportadores.exportador_markdown import ExportadorMarkdown


class TestExporters(unittest.TestCase):
    def setUp(self):
        self.base_info = ArquivoInfo("mod.txt", "h_base_123456", 100)
        self.alvo_info = ArquivoInfo("mod.txt", "h_alvo_123456", 150)
        self.relatorio = RelatorioComparacao(
            pacote_base="base.jar",
            pacote_alvo="alvo.jar",
            adicionados=[ArquivoInfo("add.txt", "h1", 10)],
            removidos=[ArquivoInfo("rem.txt", "h2", 20)],
            inalterados=[ArquivoInfo("same.txt", "h3", 30)],
            modificados=[ArquivoModificadoInfo("mod.txt", self.base_info, self.alvo_info)],
            ignorados=["META-INF/MANIFEST.MF"],
        )

    def test_json_exporter_para_dict_e_arquivo(self):
        exporter = ExportadorJSON()
        dados = exporter.para_dict(self.relatorio)

        self.assertEqual(dados["totais"]["modificados"], 1)
        self.assertEqual(dados["totais"]["adicionados"], 1)
        self.assertEqual(dados["totais"]["removidos"], 1)
        self.assertEqual(dados["totais"]["inalterados"], 1)
        self.assertEqual(dados["totais"]["ignorados"], 1)
        self.assertEqual(dados["modificados"][0]["delta_bytes"], 50)

        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_arquivo = Path(tmp_dir) / "subpasta" / "saida.json"
            exporter.exportar(self.relatorio, caminho_arquivo)

            self.assertTrue(caminho_arquivo.exists())
            with open(caminho_arquivo, "r", encoding="utf-8") as f:
                carregado = json.load(f)
            self.assertEqual(carregado["totais"]["modificados"], 1)

    def test_markdown_exporter_para_markdown_e_arquivo(self):
        exporter = ExportadorMarkdown()
        md = exporter.para_markdown(self.relatorio)

        self.assertIn("# Relatório de Comparação de Pacotes", md)
        self.assertIn("| **Modificados (Conflitos)** | 1 |", md)
        self.assertIn("`mod.txt`", md)
        self.assertIn("+50 B", md)

        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_arquivo = Path(tmp_dir) / "saida.md"
            exporter.exportar(self.relatorio, caminho_arquivo)
            self.assertTrue(caminho_arquivo.exists())
            self.assertIn("# Relatório", caminho_arquivo.read_text(encoding="utf-8"))

    def test_html_exporter_sanitizacao_e_arquivo(self):
        # Teste com caractere suspeito de XSS no nome do arquivo
        relatorio_xss = RelatorioComparacao(
            pacote_base="base<script>.jar",
            pacote_alvo='alvo"onload="alert(1).jar',
            adicionados=[ArquivoInfo("<img src=x onerror=alert(1)>.class", "hash", 100)],
        )

        exporter = ExportadorHTML()
        html = exporter.para_html(relatorio_xss)

        # Não pode conter as tags maliciosas cruas nos metadados ou arquivos
        self.assertNotIn("base<script>.jar", html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("base&lt;script&gt;.jar", html)
        self.assertIn("&lt;img src=x", html)

        # Deve conter componentes interativos
        self.assertIn('id="filtro-busca"', html)
        self.assertIn('class="btn-filtro', html)
        self.assertIn('data-tipo="adicionados"', html)

        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_arquivo = Path(tmp_dir) / "saida.html"
            exporter.exportar(relatorio_xss, caminho_arquivo)
            self.assertTrue(caminho_arquivo.exists())


if __name__ == "__main__":
    unittest.main()
