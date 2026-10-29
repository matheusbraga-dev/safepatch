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
        from safepatch import __version__
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli(["--version"])
            self.assertEqual(codigo, 0)
            self.assertIn(f"safepatch {__version__}", mock_stdout.getvalue())

    def test_cli_versao_curta_flag(self):
        from safepatch import __version__
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli(["-V"])
            self.assertEqual(codigo, 0)
            self.assertIn(f"safepatch {__version__}", mock_stdout.getvalue())

    def test_subprocesso_versao(self):
        from safepatch import __version__
        cmd = [sys.executable, str(WORKSPACE_ROOT / "main.py"), "--version"]
        res = subprocess.run(
            cmd,
            cwd=str(WORKSPACE_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn(f"safepatch {__version__}", res.stdout)

    def test_execucao_com_filtro_inclusao(self):
        cmd = [
            sys.executable,
            str(WORKSPACE_ROOT / "main.py"),
            "--base", str(SAMPLE_BASE),
            "--alvo", str(SAMPLE_ALVO),
            "-f", "*UserDTO*",
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
        self.assertIn("Total Modificados: 1", res.stdout)
        self.assertIn("Total Inalterados: 0", res.stdout)
        self.assertIn("UserDTO.class", res.stdout)

    def test_execucao_com_diretorios_locais(self):
        with tempfile.TemporaryDirectory() as dir_base, tempfile.TemporaryDirectory() as dir_alvo:
            f1 = Path(dir_base) / "servico.properties"
            f1.write_text("versao=1.0\n", encoding="utf-8")
            f2 = Path(dir_alvo) / "servico.properties"
            f2.write_text("versao=1.1\n", encoding="utf-8")

            cmd = [
                sys.executable,
                str(WORKSPACE_ROOT / "main.py"),
                "--base", str(dir_base),
                "--alvo", str(dir_alvo),
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
            self.assertIn("Total Modificados: 1", res.stdout)
            self.assertIn("servico.properties", res.stdout)

    def test_execucao_com_codigo_fonte_java_local(self):
        with tempfile.TemporaryDirectory() as dir_fonte:
            caminho_java = Path(dir_fonte) / "src" / "main" / "java" / "com" / "example" / "dto" / "UserDTO.java"
            caminho_java.parent.mkdir(parents=True)
            caminho_java.write_text(
                "package com.example.dto;\n\n"
                "public class UserDTO {\n"
                "    private Long id;\n"
                "    public String metodoNovoIDE() {\n"
                "        return \"alterado direto no fonte\";\n"
                "    }\n"
                "}\n",
                encoding="utf-8",
            )

            cmd = [
                sys.executable,
                str(WORKSPACE_ROOT / "main.py"),
                "--base", str(SAMPLE_BASE),
                "--alvo", str(dir_fonte),
                "-f", "*UserDTO*",
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
            self.assertIn("Total Modificados: 1", res.stdout)
            self.assertIn("UserDTO.class", res.stdout)
            self.assertIn("+        return \"alterado direto no fonte\";", res.stdout)

    def test_executar_cli_json_stdout_com_hifen(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--json", "-",
            ])
            self.assertEqual(codigo, 0)
            saida = mock_stdout.getvalue()
            # Deve ser parseável como JSON puro
            dados = json.loads(saida)
            self.assertEqual(dados["totais"]["modificados"], 1)
            self.assertNotIn("Iniciando varredura", saida)
            # Logs informativos vão para stderr
            self.assertIn("Iniciando varredura", mock_stderr.getvalue())

    def test_executar_cli_json_stdout_flag(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("sys.stderr", new_callable=io.StringIO):
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--json-stdout",
            ])
            self.assertEqual(codigo, 0)
            dados = json.loads(mock_stdout.getvalue())
            self.assertEqual(dados["totais"]["modificados"], 1)

    def test_executar_cli_silencioso(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--silencioso",
                "--json", "-",
            ])
            self.assertEqual(codigo, 0)
            self.assertEqual(mock_stderr.getvalue(), "")
            dados = json.loads(mock_stdout.getvalue())
            self.assertEqual(dados["totais"]["modificados"], 1)

    def test_executar_cli_eventos_progresso_ndjson(self):
        with patch("sys.stdout", new_callable=io.StringIO), patch("sys.stderr", new_callable=io.StringIO) as mock_stderr:
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--eventos-progresso",
                "--silencioso",
            ])
            self.assertEqual(codigo, 0)
            linhas_stderr = [l for l in mock_stderr.getvalue().splitlines() if l.strip()]
            self.assertTrue(len(linhas_stderr) > 0)
            for linha in linhas_stderr:
                evento = json.loads(linha)
                self.assertEqual(evento["evento"], "progresso")
                self.assertIn("etapa", evento)
                self.assertIn("percentual", evento)

    def test_executar_cli_diff_arquivo_json(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("sys.stderr", new_callable=io.StringIO):
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--diff-arquivo", "com/example/dto/UserDTO.class",
                "--json", "-",
            ])
            self.assertEqual(codigo, 0)
            dados = json.loads(mock_stdout.getvalue())
            self.assertEqual(dados["caminho"], "com/example/dto/UserDTO.class")
            self.assertEqual(dados["status"], "modificado")
            self.assertIn("diff", dados)
            self.assertTrue(len(dados["diff"]) > 0)

    def test_executar_cli_diff_arquivo_terminal(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("sys.stderr", new_callable=io.StringIO):
            codigo = executar_cli([
                "--base", str(SAMPLE_BASE),
                "--alvo", str(SAMPLE_ALVO),
                "--diff-arquivo", "com/example/dto/UserDTO.class",
                "--no-color",
            ])
            self.assertEqual(codigo, 0)
            saida = mock_stdout.getvalue()
            self.assertIn("UserDTO", saida)

    def test_executar_cli_erro_estruturado_json_stdout(self):
        with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout, patch("sys.stderr", new_callable=io.StringIO):
            codigo = executar_cli([
                "--base", "arquivo_inexistente.jar",
                "--alvo", str(SAMPLE_ALVO),
                "--json", "-",
            ])
            self.assertEqual(codigo, 1)
            dados = json.loads(mock_stdout.getvalue())
            self.assertEqual(dados["status"], "erro")
            self.assertIn("mensagem", dados)

    def test_cli_parser_flags_ssh(self):
        parser = criar_parser()
        args = parser.parse_args([
            "--base", "deploy@servidor.com:/app.jar",
            "--alvo", "local.jar",
            "--chave-ssh", "~/.ssh/id_rsa",
            "--porta-ssh", "2222",
            "--senha-ssh", "segredo",
            "--salvar-copia-local", "./backups",
        ])
        self.assertEqual(args.chave_ssh, "~/.ssh/id_rsa")
        self.assertEqual(args.porta_ssh, 2222)
        self.assertEqual(args.senha_ssh, "segredo")
        self.assertEqual(args.dir_copia_local, "./backups")

    def test_cli_execucao_com_destino_ssh_mockado(self):
        with patch("safepatch.infrastructure.remoto.resolvedor_ssh.ResolvedorCaminhoRemoto.resolver", return_value=SAMPLE_BASE) as mock_resolver, patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli([
                "--base", "deploy@cliente.com:/var/app/prod.jar",
                "--alvo", str(SAMPLE_ALVO),
                "--chave-ssh", "chave.pem",
                "--porta-ssh", "22",
                "--no-color",
            ])
            self.assertEqual(codigo, 0)
            self.assertIn("RELATÓRIO DE COMPARAÇÃO DE PACOTES", mock_stdout.getvalue())
            self.assertEqual(mock_resolver.call_count, 2)

    def test_cli_listar_remoto_json(self):
        from safepatch.infrastructure.remoto.transporte import ItemRemotoInfo

        itens_mock = [
            ItemRemotoInfo(nome="app.jar", caminho="/opt/app/app.jar", eh_diretorio=False, tamanho_bytes=1024),
        ]
        with patch("safepatch.infrastructure.remoto.resolvedor_ssh.ResolvedorCaminhoRemoto.listar_remoto", return_value=itens_mock), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli(["--listar-remoto", "deploy@servidor:/opt/app", "--json", "-"])
            self.assertEqual(codigo, 0)
            dados = json.loads(mock_stdout.getvalue())
            self.assertEqual(dados["status"], "sucesso")
            self.assertEqual(dados["total"], 1)
            self.assertEqual(dados["itens"][0]["nome"], "app.jar")

    def test_cli_publicar_sucesso(self):
        resultado_mock = {
            "status": "sucesso",
            "origem_local": "app.jar",
            "destino_remoto": "ssh://deploy@servidor/opt/app.jar",
            "backup_remoto": "/opt/app.jar.bak_20261028",
            "sha256": "abcdef123456",
            "tamanho_bytes": 1024,
        }
        with patch("safepatch.infrastructure.remoto.resolvedor_ssh.ResolvedorCaminhoRemoto.publicar_remoto", return_value=resultado_mock), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli(["--publicar", "app.jar", "deploy@servidor:/opt/app.jar", "--json", "-"])
            self.assertEqual(codigo, 0)
            dados = json.loads(mock_stdout.getvalue())
            self.assertEqual(dados["status"], "sucesso")
            self.assertEqual(dados["sha256"], "abcdef123456")

    def test_cli_publicar_erro(self):
        with patch("safepatch.infrastructure.remoto.resolvedor_ssh.ResolvedorCaminhoRemoto.publicar_remoto", side_effect=Exception("Falha de rede")), \
             patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
            codigo = executar_cli(["--publicar", "app.jar", "deploy@servidor:/opt/app.jar", "--json", "-"])
            self.assertEqual(codigo, 1)
            dados = json.loads(mock_stdout.getvalue())
            self.assertEqual(dados["status"], "erro")
            self.assertIn("Falha de rede", dados["mensagem"])


if __name__ == "__main__":
    unittest.main()

