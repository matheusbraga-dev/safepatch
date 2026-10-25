"""Testes unitários para utilitários de formatação e sanitização."""

import unittest
from tests.helpers import SRC_PATH

from safepatch.shared.formatacao import (
    formatar_bytes,
    formatar_delta,
    formatar_diff_colorido,
)
from safepatch.shared.sanitizacao import escapar_html, formatar_diff_html


class TestFormattingAndSanitization(unittest.TestCase):
    def test_formatar_bytes(self):
        self.assertEqual(formatar_bytes(500), "500 B")
        self.assertEqual(formatar_bytes(1024), "1.00 KB")
        self.assertEqual(formatar_bytes(1048576), "1.00 MB")
        self.assertEqual(formatar_bytes(-250), "-250 B")

    def test_formatar_delta(self):
        self.assertEqual(formatar_delta(25), "+25 B")
        self.assertEqual(formatar_delta(-100), "-100 B")
        self.assertEqual(formatar_delta(0), "0 B")

    def test_formatar_diff_colorido(self):
        linhas = [
            "diff --git a/test.txt b/test.txt\n",
            "--- a/test.txt\n",
            "+++ b/test.txt\n",
            "@@ -1,1 +1,1 @@\n",
            "+adicionado\n",
            "-removido\n",
            " inalterado\n",
        ]
        colorido = formatar_diff_colorido(linhas, usar_cores=True)
        self.assertIn("\033[1mdiff --git", colorido)
        self.assertIn("\033[92m+adicionado", colorido)
        self.assertIn("\033[91m-removido", colorido)
        self.assertIn("\033[96m@@", colorido)

        sem_cor = formatar_diff_colorido(linhas, usar_cores=False)
        self.assertNotIn("\033[", sem_cor)
        self.assertEqual(sem_cor, "".join(linhas))

    def test_escapar_html(self):
        texto = '<script>alert("xss & bug")</script>'
        escapado = escapar_html(texto)
        self.assertNotIn("<script>", escapado)
        self.assertIn("&lt;script&gt;", escapado)
        self.assertIn("&quot;", escapado)
        self.assertIn("&amp;", escapado)

    def test_formatar_diff_html(self):
        linhas = [
            "+<script>tag_nova</script>\n",
            "-linha_removida\n",
            "@@ -1,1 @@\n",
        ]
        html_diff = formatar_diff_html(linhas)
        self.assertIn('class="diff-line diff-add"', html_diff)
        self.assertIn("&lt;script&gt;tag_nova&lt;/script&gt;", html_diff)
        self.assertIn('class="diff-line diff-del"', html_diff)
        self.assertIn('class="diff-line diff-hunk"', html_diff)


if __name__ == "__main__":
    unittest.main()
