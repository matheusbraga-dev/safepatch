# 🛡️ SafePatch (.jar / .war / .zip)

[![PyPI version](https://img.shields.io/pypi/v/safepatch.svg)](https://pypi.org/project/safepatch/)
[![Python Versions](https://img.shields.io/pypi/pyversions/safepatch.svg)](https://pypi.org/project/safepatch/)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Uma ferramenta de linha de comando (CLI) em Python de alta performance para inspeção, auditoria e comparação de pacotes compactados (`.jar`, `.war`, `.zip`). Desenvolvida para detectar conflitos, arquivos alterados, adições e remoções entre versões de artefatos de release, patches e bibliotecas.

Zero dependências externas: construída exclusivamente com a **biblioteca padrão do Python**.

---

## 🚀 Funcionalidades

* ⚡ **Leitura Otimizada em Streaming**: Processa pacotes lendo blocos de 64KB sob demanda, permitindo analisar arquivos pesados com consumo mínimo de memória RAM.
* 💡 **Comparação Direta com Código-Fonte (`.java` vs `.class`)**: Audite alterações feitas na sua IDE diretamente contra o `.jar` de produção **sem precisar compilar ou rodar build** (`mvn package`, `gradle build`). O SafePatch mapeia os pacotes Java, normaliza comentários/espaçamento e gera o diff do que você alterou.
* 📁 **Suporte Híbrido a Pacotes, Pastas e Fontes**: Aceita arquivos `.jar`, `.war`, `.zip`, **pastas compiladas** (`target/classes`), **pastas de código-fonte** (`src/main/java`, `.`) ou arquivos `.java` individuais.
* 🔒 **Verificação de Integridade (SHA-256)**: Compara o hash SHA-256 de cada arquivo interno para garantir a detecção exata de modificações lógicas, mesmo quando as datas de modificação ou atributos forem alterados.
* 📊 **Cálculo de Variação (Delta)**: Exibe a diferença de tamanho (em bytes, KB, MB) para cada arquivo modificado (ex: `1.81 KB → 2.39 KB | +602 B`).
* ☕ **Diff Descompilado no Estilo Git (`-d / --diff`)**:
  * Mostra as linhas adicionadas (`+`) e removidas (`-`) em arquivos modificados, novos e deletados.
  * Suporta arquivos de texto puro (XML, JSON, properties, YAML, SQL, código-fonte, etc.).
  * **Descompilação Automática de Bytecode Java (.class)**: Descompila arquivos `.class` em **código-fonte Java real e limpo** (via CFR Decompiler integrado), permitindo ler métodos e classes sem ter que decifrar instruções de bytecode.
* 🎯 **Filtros Flexíveis por Padrões Glob**:
  * **Inclusão (`-f / --filtro`)**: Concentre a auditoria em classes ou pacotes específicos (ex: `-f "*UserDTO*"`, `-f "com/exemplo/servico/*"`).
  * **Exclusão (`-i / --ignorar`)**: Ignore metadados voláteis como `META-INF/*`, arquivos de documentação (`*.md`) ou logs.
* 📄 **Múltiplos Formatos de Relatório**:
  * **Console (Terminal)**: Colorido via ANSI com modo compacto ou verboso (`--verbose`).
  * **JSON (`--json`)**: Estruturado com metadados e totais, ideal para integrações e APIs.
  * **Markdown (`--markdown / --md`)**: Tabelas e diffs prontas para documentação ou Pull Requests.
  * **HTML Interativo (`--html`)**: Dashboard visual moderno e responsivo com **campo de busca instantânea**, filtros rápidos por categoria (Modificados, Adicionados, Removidos) e diffs embutidos, 100% offline (zero CDNs externas).
* 🤖 **Pronto para CI/CD (`--fail-on-conflict`)**: Retorna código de saída `2` se detectar arquivos conflitantes/modificados, permitindo travar esteiras de deploy indesejadas.

---

## 📋 Requisitos

* **Python 3.8+** (compatível com Linux, macOS e Windows).
* Java JRE/JDK 8+ instalado no sistema (para descompilação de arquivos `.class`).

---

## 🛠️ Instalação

### Via PyPI (Recomendado)

```bash
pip install safepatch
```

### Via Código-Fonte (Desenvolvimento)

```bash
git clone https://github.com/matheusbraga-dev/safepatch.git
cd safepatch
pip install -e .
```

Para validar a integridade da instalação, execute a suíte de testes:

```bash
python -m unittest discover tests
```

---

## 💻 Guia de Uso

### 1. Comparação Básica

Para comparar dois pacotes `.jar`, `.war` ou `.zip`:

```bash
safepatch --base "app-v1.0.jar" --alvo "app-v1.1.jar"
```

**Exemplo de saída no terminal:**
```text
Iniciando varredura dos pacotes...
Lendo pacote base: app-v1.0.jar...
Lendo pacote alvo: app-v1.1.jar...
Analisando diferenças e detectando conflitos...

=== RELATÓRIO DE COMPARAÇÃO DE PACOTES ===
Pacote Base: app-v1.0.jar
Pacote Alvo: app-v1.1.jar
==========================================

Total Adicionados: 0
Total Removidos:   0
Total Modificados: 1
Total Inalterados: 7
------------------------------------------

[~] ARQUIVOS MODIFICADOS (Atenção - Possíveis Conflitos):
    com/example/dto/UserDTO.class (875 B → 1.08 KB | +227 B)
```

---

### 2. Visualizando Diferenças Detalhadas Estilo Git (`--diff / -d`)

Para inspecionar o código exato das alterações (linhas adicionadas `+` e removidas `-`), utilize a flag `-d` ou `--diff`:

```bash
safepatch --base "app-v1.0.jar" --alvo "app-v1.1.jar" --diff
```

**Exemplo de saída com diff Java descompilado e colorido:**
```diff
[~] ARQUIVOS MODIFICADOS (Atenção - Possíveis Conflitos):
    com/example/dto/UserDTO.class (875 B → 1.08 KB | +227 B)
diff --git a/com/example/dto/UserDTO.class b/com/example/dto/UserDTO.class
--- a/com/example/dto/UserDTO.class
+++ b/com/example/dto/UserDTO.class
@@ -40,4 +40,8 @@
     public void setEmail(String string) {
         this.email = string;
     }
+
+    public String getDisplayName() {
+        return this.name + " (" + this.email + ")";
+    }
 }
```

> **Dica:** O diff também é automaticamente incorporado aos relatórios exportados em Markdown e HTML quando a flag `--diff` for utilizada junto com `--md` ou `--html`.
> No PowerShell (Windows), para quebrar linhas em comandos utilize o caractere de acento grave (`` ` ``) em vez da barra invertida (`\`).

---

### 3. Exportando Relatórios (JSON, Markdown e HTML)

Você pode gerar relatórios em um ou mais formatos simultaneamente:

```bash
safepatch --base "app-v1.0.jar" \
          --alvo "app-v1.1.jar" \
          --diff \
          --json relatorio.json \
          --md relatorio.md \
          --html relatorio.html
```

---

### 4. Filtrando Classes ou Pacotes Específicos (`-f / --filtro`)

Para focar a auditoria apenas nas classes ou pacotes relevantes para o seu patch:

```bash
# Audita apenas a classe UserDTO e arquivos do pacote financeiro
safepatch --base "app-v1.0.jar" \
          --alvo "app-v1.1.jar" \
          -f "*UserDTO*" \
          -f "com/empresa/financeiro/*"
```

---

### 5. Comparando Diretórios Locais e Pacotes (`pasta vs jar` ou `pasta vs pasta`)

O SafePatch aceita pastas descompactadas diretamente (como o diretório de saída do Maven `target/classes` ou Gradle `build/classes/java/main`), dispensando a necessidade de empacotar em JAR antes de analisar:

```bash
# Compara a pasta compilada local contra o JAR de produção do cliente
safepatch --base "cliente-producao.jar" \
          --alvo "target/classes" \
          --diff

# Ou compara duas pastas compiladas diretamente
safepatch --base "workspace-v1/target/classes" \
          --alvo "workspace-v2/target/classes"
```

---

### 6. Comparação Direta com Código-Fonte da IDE (`.java` vs `.class` sem Build!)

Você pode comparar o `.jar` de produção do cliente diretamente contra os arquivos `.java` que você está editando na sua IDE, **sem precisar rodar `mvn package` ou `gradle build`**:

```bash
# Compara o JAR do cliente diretamente contra a pasta de fontes da IDE
safepatch --base "cliente-producao.jar" \
          --alvo "src/main/java" \
          --diff

# Ou compare um arquivo Java específico que você acabou de alterar
safepatch --base "cliente-producao.jar" \
          --alvo "src/main/java/com/empresa/dto/UserDTO.java" \
          --diff

# Ou aponte para a raiz do projeto (ignora .git, target, build etc. automaticamente)
safepatch --base "cliente-producao.jar" \
          --alvo "." \
          -f "*Service*" \
          --diff
```

---

### 7. Ignorando Metadados ou Padrões Específicos (`-i / --ignorar`)

Para evitar falsos positivos gerados por manifests de build ou documentação:

```bash
safepatch --base "pacote_v1.jar" \
          --alvo "pacote_v2.jar" \
          -i "META-INF/*" \
          -i "*.properties"
```

---

### 8. Modo Verboso e Controle de Limite de Exibição

Por padrão, a CLI exibe no máximo 10 arquivos por categoria no console para evitar poluição. Para ver todos os arquivos:

```bash
# Exibe todos os arquivos no terminal sem paginação
safepatch --base "base.jar" --alvo "alvo.jar" --verbose

# Ou configure um limite personalizado (ex: 25 itens)
safepatch --base "base.jar" --alvo "alvo.jar" --limite 25
```

---

### 9. Integração Contínua (CI/CD)

Use a flag `--fail-on-conflict` para interromper scripts de automação se houver alterações inesperadas:

```bash
safepatch --base "base.jar" --alvo "alvo.jar" --fail-on-conflict
```

#### Códigos de Saída (Exit Codes):
| Código | Significado |
| :---: | :--- |
| `0` | Sucesso (análise concluída sem conflitos críticos). |
| `1` | Erro de execução (arquivo não encontrado, ZIP corrompido, argumentos inválidos). |
| `2` | Conflito detectado (quando executado com a flag `--fail-on-conflict`). |

---

## 📖 Referência de Parâmetros da CLI

| Parâmetro | Tipo | Descrição |
| :--- | :---: | :--- |
| `--base` | `string` | **Obrigatório.** Caminho para o pacote, diretório compilado ou código-fonte (`.jar`, `.war`, `.zip`, pasta ou `.java`). |
| `--alvo` | `string` | **Obrigatório.** Caminho para o pacote, diretório compilado ou código-fonte (`.jar`, `.war`, `.zip`, pasta ou `.java`). |
| `-f`, `--filtro` | `string` | Padrão glob de arquivos ou classes a incluir na análise (ex: `'*UserDTO*'`). Pode ser repetido. |
| `-i`, `--ignorar` | `string` | Padrão glob de arquivos a ignorar (ex: `'META-INF/*'`). Pode ser repetido. |
| `-d`, `--diff` | `flag` | Exibe a diferença detalhada do conteúdo estilo Git (linhas adicionadas e removidas em código Java legível). |
| `-v`, `--verbose` | `flag` | Exibe a lista completa de arquivos no terminal sem limites. |
| `--limite` | `int` | Quantidade máxima de itens por categoria exibidos no terminal (padrão: `10`). |
| `--no-color` | `flag` | Desativa a coloração ANSI na saída do console. |
| `--json` | `string` | Caminho do arquivo para salvar o relatório em formato JSON. |
| `--md`, `--markdown` | `string` | Caminho do arquivo para salvar o relatório em formato Markdown. |
| `--html` | `string` | Caminho do arquivo para salvar o relatório visual interativo em HTML com busca e filtros em tempo real. |
| `--fail-on-conflict` | `flag` | Encerra com código `2` caso haja arquivos modificados. |
| `-V`, `--version` | `flag` | Exibe a versão instalada do SafePatch e encerra. |
| `-h`, `--help` | `flag` | Exibe a mensagem de ajuda com todos os comandos disponíveis. |

---

## 📁 Estrutura do Projeto (Clean Architecture)

```text
cli/
├── pyproject.toml                     # Metadados e configuração de build (setuptools)
├── README.md                          # Documentação da ferramenta
├── CHANGELOG.md                       # Histórico de lançamentos e versões
├── LICENSE                            # Termos da licença de código aberto MIT
├── main.py                            # Ponto de entrada raiz
│
├── src/
│   └── safepatch/                     # Pacote principal
│       ├── __init__.py                # Exportação da API do pacote
│       ├── __main__.py                # Ponto de entrada (python -m safepatch)
│       │
│       ├── config/                    # Configurações centrais
│       │   ├── __init__.py
│       │   └── configuracoes.py       # Buffers de streaming, timeouts e limites
│       │
│       ├── domain/                    # Núcleo de domínio (regras puras, zero I/O)
│       │   ├── __init__.py
│       │   ├── modelos.py             # ArquivoInfo, ArquivoModificadoInfo, RelatorioComparacao
│       │   ├── protocolos.py          # Interfaces: ProtocoloLeitor, ProtocoloComparador, etc.
│       │   └── excecoes.py            # Hierarquia de exceções de domínio
│       │
│       ├── application/               # Casos de uso e DTOs
│       │   ├── __init__.py
│       │   ├── dtos.py                # ParametrosComparacao
│       │   └── casos_de_uso.py        # CompararPacotesCasoDeUso (orquestrador de auditoria)
│       │
│       ├── infrastructure/            # Implementações concretas de I/O
│       │   ├── __init__.py
│       │   ├── sistema_arquivos/      # Escrita atômica segura no disco (escritor_atomico.py)
│       │   ├── leitores/              # Leitores streaming (leitor_zip, leitor_diretorio, leitor_fonte, leitor_universal)
│       │   ├── comparacao/            # Comparação por conjuntos e filtros glob (comparador_conjuntos.py)
│       │   ├── descompilador/         # Descompilador CFR com subprocess seguro e timeout (executor_cfr.py)
│       │   ├── diff/                  # Motor de unified diff Git (motor_diff.py)
│       │   └── exportadores/          # Exportadores isolados (exportador_json, markdown, html)
│       │
│       ├── presentation/              # Camada de apresentação e CLI
│       │   ├── __init__.py
│       │   ├── cli.py                 # Parser argparse e controle de exit codes
│       │   └── console.py             # Renderizador de terminal com cores ANSI (RenderizadorConsole)
│       │
│       ├── shared/                    # Utilitários compartilhados
│       │   ├── __init__.py
│       │   ├── formatacao.py          # Formatação de bytes, deltas e diff colorido
│       │   ├── normalizador_java.py   # Normalização e extração semântica de código Java
│       │   └── sanitizacao.py         # Sanitização e escape HTML contra XSS
│       │
│       └── bin/                       # Binários embutidos
│           └── cfr.jar                # Descompilador CFR
│
└── tests/                             # Suíte de testes automatizados
    ├── __init__.py
    ├── helpers.py                     # Fixtures e geradores temporários
    ├── unit/                          # Testes unitários isolados
    ├── integration/                   # Testes de integração (Use Cases)
    └── cli/                           # Testes funcionais da interface de linha de comando
```

---

## 🧪 Executando os Testes

Para rodar todos os testes automatizados:

```bash
python -m unittest discover tests
```

Para rodar em modo detalhado (verbose):

```bash
python -m unittest discover tests -v
```

---

## 📄 Licença

Este projeto é disponibilizado sob a licença [MIT](LICENSE). Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
