# 🧼 CSV Cleaner — Streamlit Data Cleaning Pipeline

Aplicação em **Python + Streamlit** para **carregar um CSV**, executar **limpeza de dados passo a passo** (com opções por etapa) e **baixar o arquivo final tratado** pronto para análise/BI/ML.

GitHub: https://github.com/CostaPaiiva

---

## ✨ O que o sistema faz

- Upload de arquivo **.csv**
- Diagnóstico rápido (linhas/colunas, nulos, duplicadas, tipos)
- Limpeza guiada por etapas (você decide o que aplicar)
- Exportação do dataset tratado em **CSV compatível com Excel (PT-BR)**:
  - separador `;`
  - encoding `utf-8-sig` (UTF-8 com BOM)  
  ✅ Isso garante que o Excel abra com **cada coluna no lugar certo** (A=age, B=sex, C=bmi…).

---

## ✅ Funcionalidades (passo a passo)

### 1) Upload e leitura
- Upload de CSV pela sidebar
- Escolha do separador: `,` `;` `\t` `|`
- Detecção automática de encoding (fallback incluso)
- Configuração de valores interpretados como NA (`NA`, `null`, `NaN`, etc.)

### 2) Diagnóstico do dataset
- Prévia do dataset
- Resumo geral:
  - total de linhas e colunas
  - nulos totais
  - linhas duplicadas
- Resumo por coluna:
  - dtype
  - contagem e % de nulos
  - valores únicos

### 3) Limpeza / Tratamento
- **Padronização de nomes de colunas**
  - minúsculas, `_` no lugar de espaços, remove caracteres especiais
  - **garante nomes únicos** (`col`, `col_2`, `col_3`…)
  - indicador de “possíveis duplicados” após padronizar
- **Limpeza de texto**
  - `strip()` (remove espaços no início/fim)
  - normalização de múltiplos espaços
- **Tipagem automática**
  - tenta converter texto → número (inclui formatos tipo `1.234,56`)
  - tenta converter texto → data/hora (`datetime`)
- **Remoção de duplicadas**
- **Tratamento de nulos**
  - numéricas: 0 / média / mediana / remover linhas
  - texto: `DESCONHECIDO` / moda / remover linhas
  - datas: mínimo / máximo / remover linhas
- **Outliers (opcional)**
  - remoção por IQR (Q1−k·IQR, Q3+k·IQR)
- **Remover colunas (opcional)**

### 4) Exportação
- Download do **CSV tratado** com separador `;` e `utf-8-sig` para abrir corretamente no Excel.

---

## 🧰 Tecnologias
- Python
- Streamlit
- Pandas / NumPy
- chardet (detecção de encoding)
- python-dateutil (parse de datas)

---

## 📦 Instalação

### 1) Clone o repositório
> Substitua `NOME_DO_REPO` pelo nome do seu repositório.

git clone https://github.com/CostaPaiiva/NOME_DO_REPO.git
cd NOME_DO_REPO

2) (Opcional) Crie e ative um ambiente virtual
Windows

python -m venv .venv
.venv\Scripts\activate
Linux / macOS

python -m venv .venv
source .venv/bin/activate

3) Instale as dependências
pip install -r requirements.txt

▶️ Como rodar
streamlit run app.py
O app geralmente abre em:

http://localhost:8501

📁 Estrutura do projeto
.
├── app.py
├── requirements.txt
└── README.md

📝 Observações importantes
CSV não salva “layout da tela”
CSV é só dados tabulares (linhas/colunas). Ele não guarda “divisões visuais”.
Por isso a exportação foca em compatibilidade e reuso.

Excel abrindo tudo na coluna A?
Isso é típico quando o Excel espera ; (configuração regional PT-BR).
Este projeto exporta com:

sep=";"

utf-8-sig

Assim, ao abrir no Excel:

Coluna A = age

Coluna B = sex

Coluna C = bmi

etc.


🤝 Contribuições
Contribuições são bem-vindas!

melhorias de performance para arquivos grandes

novos métodos de imputação

novas validações e regras

melhorias de UI/UX no Streamlit