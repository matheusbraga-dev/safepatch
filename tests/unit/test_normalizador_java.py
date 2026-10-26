"""Testes unitários para o normalizador de código Java e remoção de cabeçalhos CFR."""

import unittest
from safepatch.shared.normalizador_java import (
    extrair_declaracao_pacote,
    normalizar_codigo_java,
    remover_cabecalho_cfr,
    sao_codigos_java_equivalentes,
)


class TestNormalizadorJava(unittest.TestCase):
    def test_extrair_declaracao_pacote(self):
        codigo_com_pacote = """
        /* Licença MIT */
        package com.empresa.sistema.service;

        public class MeuServico {}
        """
        self.assertEqual(extrair_declaracao_pacote(codigo_com_pacote), "com.empresa.sistema.service")

        codigo_espacado = "package   org.exemplo.dto   ; \n public class Dto {}"
        self.assertEqual(extrair_declaracao_pacote(codigo_espacado), "org.exemplo.dto")

        codigo_default = "public class DefaultPackageClass {}"
        self.assertEqual(extrair_declaracao_pacote(codigo_default), "")

    def test_normalizar_codigo_java_remove_comentarios_e_espacos(self):
        codigo = """
        package com.exemplo;

        /**
         * Javadoc da classe
         */
        public class Exemplo {
            // Comentário de linha
            private int valor = 10; /* Comentário inline */

            public void test() {
                // Outro comentário
            }
        }
        """
        normalizado = normalizar_codigo_java(codigo)
        self.assertNotIn("Javadoc da classe", normalizado)
        self.assertNotIn("Comentário de linha", normalizado)
        self.assertNotIn("Comentário inline", normalizado)
        self.assertIn("public class Exemplo {", normalizado)
        self.assertIn("private int valor = 10;", normalizado)

    def test_remover_cabecalho_cfr(self):
        linhas_cfr = [
            "/*\n",
            " * Decompiled with CFR 0.152.\n",
            " */\n",
            "\n",
            "package com.exemplo;\n",
            "\n",
            "public class A {}\n",
        ]
        limpo = remover_cabecalho_cfr(linhas_cfr)
        self.assertEqual(limpo[0], "package com.exemplo;\n")
        self.assertEqual(limpo[2], "public class A {}\n")

        linhas_sem_cfr = ["package com.exemplo;\n", "public class B {}\n"]
        self.assertEqual(remover_cabecalho_cfr(linhas_sem_cfr), linhas_sem_cfr)

    def test_sao_codigos_java_equivalentes(self):
        codigo_cfr = """
        /*
         * Decompiled with CFR.
         */
        package com.exemplo;

        public class Usuario {
            private String nome;

            public String getNome() {
                return this.nome;
            }
        }
        """
        codigo_humano = """
        package com.exemplo;

        // Classe de usuário do domínio
        public class Usuario {
            /* Nome do cliente */
            private String nome;

            public String getNome() {
                return this.nome;
            }
        }
        """
        codigo_alterado = """
        package com.exemplo;

        public class Usuario {
            private String nome;
            private String email;

            public String getNome() {
                return this.nome;
            }
        }
        """
        self.assertTrue(sao_codigos_java_equivalentes(codigo_cfr, codigo_humano))
        self.assertFalse(sao_codigos_java_equivalentes(codigo_cfr, codigo_alterado))

    def test_normalizar_com_bom_utf8(self):
        codigo_com_bom = "\ufeffpackage com.exemplo.dto;\n\npublic class TestDTO {}"
        self.assertEqual(extrair_declaracao_pacote(codigo_com_bom), "com.exemplo.dto")
        norm = normalizar_codigo_java(codigo_com_bom)
        self.assertFalse(norm.startswith("\ufeff"))
        self.assertTrue(norm.startswith("package com.exemplo.dto;"))

    def test_equivalencia_com_parametros_sinteticos_cfr(self):
        # CFR gera parâmetros l, string, string2
        codigo_descompilado = """
        package com.example.dto;
        public class UserDTO {
            private Long id;
            private String name;
            public UserDTO(Long l, String string) {
                this.id = l;
                this.name = string;
            }
            public void setId(Long l) {
                this.id = l;
            }
        }
        """
        # Humano escreve nomes reais: id, name
        codigo_humano = """
        \ufeffpackage com.example.dto;
        import java.io.Serializable;
        public class UserDTO {
            private Long id;
            private String name;
            // Construtor completo
            public UserDTO(Long id, String name) {
                this.id = id;
                this.name = name;
            }
            public void setId(Long id) {
                this.id = id;
            }
        }
        """
        self.assertTrue(sao_codigos_java_equivalentes(codigo_descompilado, codigo_humano))


if __name__ == "__main__":
    unittest.main()

