# OpenMeteoAgent
Agente LLM com Tool de Previsão do Tempo (OpenMeteo)

# Agente de Previsão do Tempo

Projeto de desafio técnico que conecta um modelo local via **Ollama** a
uma ferramenta de previsão do tempo utilizando a API **Open-Meteo**.\
O agente recebe perguntas do usuário, chama a função
`get_daily_forecast(lat, lon, days_ahead)` quando necessário e retorna a
resposta em **português do Brasil**.

------------------------------------------------------------------------

# Estrutura do Projeto

    .
    ├── main.py          # Lógica principal do agente e integração com o modelo
    ├── tool.py          # Implementação da função de previsão do tempo
    ├── app_gradio.py    # Interface web simples usando Gradio
    └── README.md

------------------------------------------------------------------------

# Dependências

Instale as dependências com:

``` bash
pip install openai gradio requests
```

Também é necessário ter o **Ollama** instalado.

Instalação do Ollama:\
https://ollama.com/download

------------------------------------------------------------------------

# Como Rodar

## 1. Baixar um modelo no Ollama

Exemplo:

``` bash
ollama pull llama3.2:1b
```

## 2. Iniciar o Ollama

``` bash
ollama serve
```

Por padrão ele ficará disponível em:

    http://localhost:11434

------------------------------------------------------------------------

## 3. (Opcional) Configurar variáveis de ambiente

``` bash
export OLLAMA_BASE_URL=http://localhost:11434/v1
export OLLAMA_API_KEY=ollama
export OLLAMA_MODEL=llama3.2:1b
export LOG_LEVEL=INFO
```

------------------------------------------------------------------------

## 4. Rodar a aplicação

``` bash
python app_gradio.py
```

O terminal exibirá um link semelhante a:

    Running on http://127.0.0.1:7860

Abra esse endereço no navegador.

------------------------------------------------------------------------

# Como Validar a Execução

A aplicação está funcionando corretamente quando:

-   A interface abre no navegador
-   Perguntas geram respostas do modelo
-   O modelo chama automaticamente a ferramenta de previsão
-   A resposta final apresenta dados estruturados de previsão

Os dados retornados incluem:

-   `temperature_2m_max`
-   `temperature_2m_min`
-   `precipitation_sum`
-   data e unidade de medida

------------------------------------------------------------------------

# Regras da Ferramenta

A função `get_daily_forecast` espera os seguintes parâmetros:

  Parâmetro    Descrição
  ------------ -----------------------------------------
  lat          Latitude entre **-90 e 90**
  lon          Longitude entre **-180 e 180**
  days_ahead   Número de dias de previsão (**1 a 16**)

Entradas inválidas geram mensagens de erro apropriadas.

------------------------------------------------------------------------

# Exemplos de Entrada e Saída

## Exemplo 1

### Entrada

    Quero a previsão do tempo para latitude -23.55 longitude -46.63 para os próximos 3 dias.

### Saída esperada

    2026-03-12
    temperature_2m_max: 28 °C
    temperature_2m_min: 19 °C
    precipitation_sum: 4 mm

    2026-03-13
    temperature_2m_max: 27 °C
    temperature_2m_min: 18 °C
    precipitation_sum: 2 mm

    2026-03-14
    temperature_2m_max: 26 °C
    temperature_2m_min: 17 °C
    precipitation_sum: 0 mm

------------------------------------------------------------------------

## Exemplo 2

### Entrada

    Me passe a previsão do tempo para os próximos 5 dias.

### Saída esperada

    Informe latitude, longitude e o período desejado.

------------------------------------------------------------------------

## Exemplo 3

### Entrada

    Quero previsão para lat -120 lon 10 para 3 dias.

### Saída esperada

    Latitude deve estar entre -90 e 90.

------------------------------------------------------------------------

# Observações

-   A previsão do tempo utiliza a API pública **Open-Meteo**.
-   O agente utiliza **function calling** compatível com o formato da
    API OpenAI.
-   O projeto inclui tratamento básico de erros:
    -   validação de parâmetros
    -   falha de requisição HTTP
    -   resposta JSON inválida
    -   ausência de dados de previsão
