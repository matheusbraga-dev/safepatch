"""Testes para a interface de linha de comando (CLI)."""

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.helpers import SAMPLE_ALVO, SAMPLE_BASE, SRC_PATH, WORKSPACE_ROOT

from safepatch.presentation.cli import criar_parser, executar_cli


class TestCLI(unittest.TestCase):
    def test_parser_configuracao(self):
        parser = criar_parser()
        args = parser.parse_args(["--base", "base.jar", "--alvo", "alvo.jar", "-d", "--no-color"])
        self.assertEqual(args.base, "base.jar")
        self.assertEqual(args.alvo, "alvo.jar")
        self.assertTrue(args.diff)
        self.assertTrue(args.no_color)

    def test_executar_cli_sucesso(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--no-color",
            ])
            self.assertEqual(codigo, 0)
            saida = mock_stdout.getvalue()
            self.assertIn("RELATÓRIO DE COMPARAÇÃO DE PACOTES", saida)
            self.assertIn("Total Modificados: 1", saida)

    def test_executar_cli_fail_on_conflict(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--fail-on-conflict",
                "--no-color",
            ])
            self.assertEqual(codigo, 2)
            saida = mock_stdout.getvalue()
            self.assertIn("[FALHA CI/CD]", saida)

    def test_executar_cli_arquivo_inexistente(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli([
                "--base", "nao_existe.jar",
                "--alvo", str(SAMPLE_ALVO),
            ])
            self.assertEqual(codigo, 1)
            saida = mock_stdout.getvalue()
            self.assertIn("Erro: O arquivo 'nao_existe.jar' não foi encontrado.", saida)

    def test_executar_cli_extensao_invalida(self):
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
            temp_txt = f.name
        self.addCleanup(lambda: os.path.exists(temp_txt) and os.remove(temp_txt))

        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli([
                "--base", temp_txt,
                "--alvo", str(SAMPLE_ALVO),
            ])
            self.assertEqual(codigo, 1)
            saida = mock_stdout.getvalue()
            self.assertIn("não parece ser um pacote compactado", saida)

    def test_execucao_subprocesso_main(self):
        cmd = [
            sys.executable,
            str(WORKSPACE_ROOT / "main.py"),
            "--base", str(SAMPLE_BASE),
            "--alvo", str(SAMPLE_ALVO),
            "--no-color",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("UserDTO.class", res.stdout)

    def test_execucao_com_diff(self):
        cmd = [
            sys.executable,
            str(WORKSPACE_ROOT / "main.py"),
            "--base", str(SAMPLE_BASE),
            "--alvo", str(SAMPLE_ALVO),
            "--diff",
            "--no-color",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("diff --git", res.stdout)
        self.assertIn("getDisplayName", res.stdout)

    def test_execucao_com_filtro_glob(self):
        cmd = [
            sys.executable,
            str(WORKSPACE_ROOT / "main.py"),
            "--base", str(SAMPLE_BASE),
            "--alvo", str(SAMPLE_ALVO),
            "-i", "*.class",
            "--no-color",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("Total Modificados: 0", res.stdout)
        self.assertIn("Total Ignorados:   7", res.stdout)

    def test_execucao_com_exportacao_completa(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            caminho_json = Path(tmp_dir) / "relatorio.json"
            caminho_md = Path(tmp_dir) / "relatorio.md"
            caminho_html = Path(tmp_dir) / "relatorio.html"

            cmd = [
                sys.executable,
                str(WORKSPACE_ROOT / "main.py"),
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--json", str(caminho_json),
                "--md", str(caminho_md),
                "--html", str(caminho_html),
                "--no-color",
            ]
            res = subprocess.run(
                cmd,
                cwd=str(WORKSPACE_ROOT),
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(res.returncode, 0)
            self.assertTrue(caminho_json.exists())
            self.assertTrue(caminho_md.exists())
            self.assertTrue(caminho_html.exists())

    def test_cli_versao_flag(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli(["--version"])
            self.assertEqual(codigo, 0)
            self.assertIn("safepatch 1.0.0", mock_stdout.getvalue())

    def test_cli_versao_curta_flag(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli(["-V"])
            self.assertEqual(codigo, 0)
            self.assertIn("safepatch 1.0.0", mock_stdout.getvalue())

    def test_subprocesso_versao(self):
        cmd = [sys.executable, str(WORKSPACE_ROOT / "main.py"), "--version"]
        res = subprocess.run(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("safepatch 1.0.0", res.stdout)


if __name__ == "__main__":
    unittest.main()

