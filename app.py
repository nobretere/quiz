import streamlit as st
import os
import tempfile
from PyPDF2 import PdfReader
import docx2txt
import openai
import pandas as pd
import re
from dotenv import load_dotenv

load_dotenv()

# Certifique-se de que a importação e inicialização do cliente OpenAI estejam corretas
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def get_text_from_files(files):
    text = ""
    for uploaded_file in files:
        # Detecção do tipo de arquivo pela extensão
        _, extension = os.path.splitext(uploaded_file.name)
        extension = extension.lower()

        # Processamento de PDF
        if extension == '.pdf':
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text += page.extract_text()

        # Processamento de DOCX
        elif extension == '.docx':
            tfile = tempfile.NamedTemporaryFile(delete=False)
            tfile.write(uploaded_file.read())
            doc_path = tfile.name
            text += docx2txt.process(doc_path)
            tfile.close()
            os.unlink(tfile.name)
        
        # Processamento de DOC (caso você adicione suporte a isso)
        elif extension == '.doc':
            # Implementar código para ler arquivos DOC aqui
            pass

        # Processamento de TXT
        elif extension == '.txt':
            uploaded_file.seek(0)
            file_content = uploaded_file.read().decode()
            file_content = file_content.replace('\ufeff', '')  # Remove BOM e outros caracteres especiais, se necessário
            text += file_content

        else:
            # Tipo de arquivo não suportado
            text += f"\n[Error: arquivo {uploaded_file.name} não suportado]\n"

    return text

def get_text_chunks(text):
    chunks = text.split('\n')  # Dividir por dois caracteres de nova linha
    #print(f"Total de parágrafos: {len(chunks)}")  # Isso imprimirá o número total de parágrafos
    # Adicionar um loop para imprimir cada parágrafo
    #for i, chunk in enumerate(chunks):
        #print(f"Parágrafo {i+1}: {chunk[:500]}...")  # Imprime os primeiros 50 caracteres de cada parágrafo para uma visualização rápida
        
    return chunks

def send_paragraph_to_openai(paragraph, training_goal, training_theme):
    try:
        
        # Aqui está o prompt que você está enviando para a GPT-3
        user_content = f"""GPT-3, por favor, crie três perguntas de múltipla escolha (MCQ), não utilize o termo - de acordo com o texto, ou similar - As perguntas devem ser baseadas em benefícios destacados, sem introduções ou comentários adicionais. Cada pergunta deve ter 4 opções de resposta, sendo a letra A sempre a correta. Inclua uma dica bônus de até 160 caracteres para quem acertar, e uma explicação curta e direta de até 160 caracteres para quem errar. Evite repetições e ambiguidades nas opções de resposta. Certifique-se de que todas as partes da resposta estejam completas e não sejam cortadas. O contexto é {training_goal} {training_theme}. O formato deve ser:
        Pergunta:
        [Insira a pergunta aqui]
        A) [Insira a resposta correta aqui]
        B) [Insira uma opção incorreta aqui]
        C) [Insira outra opção incorreta aqui]
        D) [Insira a última opção incorreta aqui]
        Dica Bônus para quem acertou:
        [Insira uma dica bônus aqui]
        Explicação para quem errrou:
        [Insira a explicação aqui]"""

        response = client.chat.completions.create(model="gpt-4-1106-preview",
        messages=[
            {
                "role": "system",
                "content": user_content
            },
            {
                "role": "user",
                "content": paragraph
            }
        ],
        temperature=1,
        max_tokens=500,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0)
        # Caso queira ver a qualidade do texto que está sendo analisado pela API, descomente as linhas abaixo
        #print("Parágrafo enviado para a API OpenAI:")
        #print(paragraph)

        if response.choices:
            formatted_response = response.choices[0].message.content.strip()

            # Inclui o parágrafo original no topo da resposta
            final_output = f"Parágrafo Original:\n{paragraph}\n\n{formatted_response}"

            #print("Resposta da API OpenAI:")
            #print(final_output)

            return formatted_response
        else:
            return "Nenhuma escolha retornada pela API da OpenAI"
            
    except openai.OpenAIError as e:
        return f"Erro ao acessar a API da OpenAI: {str(e)}"


def main():
    st.header("Gerador de Quiz :books:")
    
    # Campos de entrada para o objetivo e tema do treinamento
    training_goal = st.text_input("Objetivo do Treinamento:")
    training_theme = st.text_input("Tema do Treinamento:")

    with st.sidebar:
        uploaded_files = st.file_uploader("Upload seus arquivos aqui:", accept_multiple_files=True)
        
        # Flag para determinar se devemos processar os arquivos
        should_process = st.button("Processar")
    
    # Este subheader aparecerá abaixo do "Gerador de Quiz :books:"
    st.subheader("Perguntas Geradas:")
    
    paragraphs = []  # Inicializa paragraphs como uma lista vazia
    
    # Lista para armazenar os dados que serão salvos no Excel
    all_data = []
    
    if should_process and uploaded_files:
        # Extrai o texto dos arquivos carregados
        extracted_text = get_text_from_files(uploaded_files)
        print(repr(extracted_text))

        # Divide o texto em parágrafos
        paragraphs = get_text_chunks(extracted_text)
        
        #print(f"Total de parágrafos: {len(paragraphs)}")  # Imprime o número total de parágrafos

        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip() and len(paragraph.strip()) > 50:
                print(f"Processando parágrafo {i+1}:")
                mcq = send_paragraph_to_openai(f"{paragraph}", training_goal, training_theme)
                
                # Processamento para extrair as partes da resposta
                questions_parts = re.split(r'\n[A-D]\) |\nDica Bônus para quem acertou:|\nExplicação para quem errou:', mcq)
                if len(questions_parts) >= 7:
                    question_data = {
                        "Parágrafo": paragraph,
                        "Pergunta": questions_parts[0].split('\n')[-1].strip(),
                        "Resposta A": questions_parts[1].strip(),
                        "Resposta B": questions_parts[2].strip(),
                        "Resposta C": questions_parts[3].strip(),
                        "Resposta D": questions_parts[4].split('\n')[0].strip(),
                        "Dica": questions_parts[5].strip(),
                        "Explicação": questions_parts[6].strip()
                    }
                    all_data.append(question_data)

                st.markdown(f"```\n{mcq}\n```")
            else:
                print(f"Parágrafo {i+1} ignorado por ser vazio ou muito curto.")
                pass

    # Criação do DataFrame
    if all_data:
        df_new = pd.DataFrame(all_data)

        # Caminho para o arquivo Excel
        excel_path = 'saida.xlsx'

        # Verificação e combinação com arquivo existente
        if os.path.exists(excel_path):
            df_existing = pd.read_excel(excel_path)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
        else:
            df_combined = df_new

        # Salvando o DataFrame
        df_combined.to_excel(excel_path, index=False)
        st.write(f"Dados salvos em {excel_path}")

if __name__ == '__main__':
    main()






