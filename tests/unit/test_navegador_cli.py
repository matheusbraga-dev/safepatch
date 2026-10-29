"""Testes unitários para o navegador interativo de diretórios remotos na CLI."""

import unittest
from unittest.mock import MagicMock, patch

from safepatch.infrastructure.remoto.transporte import ItemRemotoInfo
from safepatch.presentation.navegador_cli import NavegadorRemotoTerminal, formatar_tabela_remota


class TestNavegadorCLI(unittest.TestCase):
    def test_formatar_tabela_remota(self):
        itens = [
            ItemRemotoInfo(nome="..", caminho="/opt", eh_diretorio=True),
            ItemRemotoInfo(nome="libs", caminho="/opt/app/libs", eh_diretorio=True),
            ItemRemotoInfo(nome="app.jar", caminho="/opt/app/app.jar", eh_diretorio=False, tamanho_bytes=1048576, modificado_em="2026-10-28T22:00:00Z"),
            ItemRemotoInfo(nome="application.yml", caminho="/opt/app/application.yml", eh_diretorio=False, tamanho_bytes=512),
        ]

        tabela = formatar_tabela_remota(
            itens=itens,
            caminho_atual="/opt/app",
            servidor="ssh://deploy@servidor:22/opt/app",
            indice_selecionado=2,
        )

        self.assertIn("Servidor:  ssh://deploy@servidor:22/opt/app", tabela)
        self.assertIn("Diretório: /opt/app", tabela)
        self.assertIn("[DIR]", tabela)
        self.assertIn("[JAR]", tabela)
        self.assertIn("[ARQ]", tabela)
        self.assertIn("libs/", tabela)
        self.assertIn("app.jar", tabela)
        self.assertIn("1.0 MB", tabela)
        self.assertIn("Total: 4 itens (2 pastas, 2 arquivos)", tabela)
        # Verifica marcador de seleção no índice 2 (app.jar)
        self.assertIn(">   [3] [JAR]", tabela)

    def test_exibir_listagem_adiciona_pai_e_imprime(self):
        resolvedor_mock = MagicMock()
        resolvedor_mock.listar_remoto.return_value = [
            ItemRemotoInfo(nome="app.jar", caminho="/opt/app/app.jar", eh_diretorio=False, tamanho_bytes=2048),
        ]

        navegador = NavegadorRemotoTerminal(resolvedor_mock)
        with patch("builtins.print") as mock_print:
            itens_retornados = navegador.exibir_listagem("deploy@servidor:/opt/app")

            self.assertEqual(len(itens_retornados), 2)
            self.assertEqual(itens_retornados[0].nome, "..")
            self.assertEqual(itens_retornados[0].caminho, "/opt")
            self.assertEqual(itens_retornados[1].nome, "app.jar")
            mock_print.assert_called_once()

    def test_navegar_interativo_selecao_arquivo(self):
        resolvedor_mock = MagicMock()
        resolvedor_mock.listar_remoto.return_value = [
            ItemRemotoInfo(nome="app-producao.jar", caminho="/opt/app/app-producao.jar", eh_diretorio=False, tamanho_bytes=4096),
        ]

        navegador = NavegadorRemotoTerminal(resolvedor_mock)
        # Simula usuário pressionando ENTER no item (índice 0 é '..', índice 1 é app-producao.jar)
        with patch.object(navegador, "_ler_entrada_teclado", side_effect=["DOWN", "ENTER"]):
            with patch("builtins.print"):
                selecionado = navegador.navegar_interativo("deploy@servidor:/opt/app")
                self.assertEqual(selecionado, "/opt/app/app-producao.jar")


if __name__ == "__main__":
    unittest.main()
