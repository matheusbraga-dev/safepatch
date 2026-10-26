"""Utilitários de normalização e extração semântica para código-fonte Java."""

import re
from typing import List, Optional


def extrair_declaracao_pacote(conteudo: str) -> str:
    """Extrai o nome do pacote declarado em um arquivo de código-fonte Java.

    Exemplo:
        'package com.empresa.service;' -> 'com.empresa.service'
    """
    if not conteudo:
        return ""
    conteudo_limpo = conteudo.replace("\ufeff", "")
    match = re.search(r"^\s*package\s+([\w\.]+)\s*;", conteudo_limpo, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def _normalizar_parametros_metodos(codigo: str) -> str:
    """Substitui nomes de parâmetros em métodos/construtores e seus corpos por marcadores canônicos.

    Isso neutraliza a divergência entre nomes sintéticos gerados pelo descompilador
    (ex: 'Long l, String string') e nomes originais da IDE (ex: 'Long id, String name').
    """
    # 1. Mascara literais de strings temporariamente para evitar chaves e variáveis falsas
    strings: List[str] = []

    def mascarar_str(m: re.Match) -> str:
        idx = len(strings)
        strings.append(m.group(0))
        return f"___LIT_STR_{idx}___"

    codigo_mascarado = re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', mascarar_str, codigo)

    # 2. Padrão para cabeçalho de método ou construtor Java
    padrao_cabecalho = re.compile(
        r"((?:public|protected|private|static|final|synchronized|abstract|\s)*"
        r"[\w<>\[\],\s]+\s+(\w+)\s*\(([^)]*)\)\s*(?:throws\s+[\w\s,]+)?\s*\{)",
        re.MULTILINE,
    )

    partes: List[str] = []
    ultimo_indice = 0

    for match in padrao_cabecalho.finditer(codigo_mascarado):
        inicio_bloco = match.start()
        if inicio_bloco < ultimo_indice:
            continue

        abertura_chaves = match.end() - 1
        params_str = match.group(3).strip()

        # Encontra o fechamento da chave correspondente por profundidade
        profundidade = 1
        atual = abertura_chaves + 1
        tamanho_total = len(codigo_mascarado)
        while atual < tamanho_total and profundidade > 0:
            char = codigo_mascarado[atual]
            if char == "{":
                profundidade += 1
            elif char == "}":
                profundidade -= 1
            atual += 1

        if profundidade != 0:
            continue

        corpo = codigo_mascarado[abertura_chaves + 1 : atual - 1]

        if params_str:
            lista_params = [p.strip() for p in params_str.split(",") if p.strip()]
            novos_params: List[str] = []
            corpo_norm = corpo
            for idx, p in enumerate(lista_params):
                tokens = p.split()
                if len(tokens) >= 2:
                    tipo_param = " ".join(tokens[:-1])
                    nome_param = tokens[-1]
                    marcador = f"__p_{idx}__"
                    novos_params.append(f"{tipo_param} {marcador}")
                    # Substitui apenas ocorrências do parâmetro NÃO precedidas por ponto
                    corpo_norm = re.sub(r"(?<!\.)\b" + re.escape(nome_param) + r"\b", marcador, corpo_norm)
                else:
                    novos_params.append(p)

            cabecalho_antigo = match.group(1)
            inicio_paren = cabecalho_antigo.find("(")
            fim_paren = cabecalho_antigo.rfind(")")
            novo_cabecalho = (
                cabecalho_antigo[: inicio_paren + 1]
                + ", ".join(novos_params)
                + cabecalho_antigo[fim_paren:]
            )

            partes.append(codigo_mascarado[ultimo_indice:inicio_bloco])
            partes.append(f"{novo_cabecalho}{corpo_norm}}}")
            ultimo_indice = atual
        else:
            partes.append(codigo_mascarado[ultimo_indice:atual])
            ultimo_indice = atual

    partes.append(codigo_mascarado[ultimo_indice:])
    resultado = "".join(partes)

    # Restaura literais de string
    for idx, s in enumerate(strings):
        resultado = resultado.replace(f"___LIT_STR_{idx}___", s)

    return resultado


def normalizar_codigo_java(codigo: str) -> str:
    """Normaliza o código-fonte Java removendo comentários e padronizando semântica.

    Permite confrontar semântica e lógica entre o código-fonte escrito por humanos
    e o código descompilado gerado a partir de bytecode .class.
    """
    if not codigo:
        return ""

    # 1. Remove UTF-8 BOM em qualquer posição
    codigo = codigo.replace("\ufeff", "")

    # 2. Remove comentários de bloco /* ... */ (incluindo Javadoc e cabeçalhos de descompilador)
    codigo = re.sub(r"/\*.*?\*/", "", codigo, flags=re.DOTALL)

    # 3. Remove comentários de linha // ...
    codigo = re.sub(r"//.*", "", codigo)

    # 4. Remove anotações exclusivas de tempo de compilação sem efeito no bytecode
    codigo = re.sub(r"^\s*@Override\b\s*", "", codigo, flags=re.MULTILINE)

    # 5. Remove imports (o compilador javac descarta imports não utilizados no bytecode;
    # os tipos reais utilizados continuam validados nas declarações e corpos de métodos)
    codigo = re.sub(r"^\s*import\s+[\w\.\*]+;\s*$", "", codigo, flags=re.MULTILINE)

    # 6. Normaliza nomes de parâmetros de métodos/construtores
    codigo = _normalizar_parametros_metodos(codigo)

    # 7. Normaliza uso do qualificador 'this.'
    codigo = re.sub(r"\bthis\.", "", codigo)

    # 8. Normaliza espaçamento linha a linha
    linhas_normalizadas: List[str] = []
    for linha in codigo.splitlines():
        linha_limpa = " ".join(linha.strip().split())
        if linha_limpa:
            linhas_normalizadas.append(linha_limpa)

    return "\n".join(linhas_normalizadas)


def remover_cabecalho_cfr(linhas: List[str]) -> List[str]:
    """Remove o bloco inicial de comentários gerado pelo descompilador CFR."""
    if not linhas:
        return []

    # Procura se as primeiras linhas contêm a assinatura do CFR
    primeiras_linhas = "".join(linhas[:10])
    if "Decompiled with CFR" in primeiras_linhas or "/*\n * Decompiled with CFR" in primeiras_linhas:
        idx_fim_comentario = 0
        for i, linha in enumerate(linhas):
            if "*/" in linha:
                idx_fim_comentario = i + 1
                break
        # Pula eventuais linhas em branco após o cabeçalho
        while idx_fim_comentario < len(linhas) and not linhas[idx_fim_comentario].strip():
            idx_fim_comentario += 1
        return [l.replace("\ufeff", "") for l in linhas[idx_fim_comentario:]]

    return [l.replace("\ufeff", "") for l in linhas]


def sao_codigos_java_equivalentes(codigo_a: str, codigo_b: str) -> bool:
    """Verifica se dois trechos de código Java possuem equivalência lógica, desconsiderando comentários e estilo."""
    return normalizar_codigo_java(codigo_a) == normalizar_codigo_java(codigo_b)

