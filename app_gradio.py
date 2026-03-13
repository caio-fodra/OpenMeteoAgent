import gradio as gr
from main import run_weather_chat

demo = gr.ChatInterface(
    fn=run_weather_chat,
    title="Agente de Previsão do Tempo",
    textbox=gr.Textbox(label="Pergunta"),
)

if __name__ == "__main__":
    demo.launch()
