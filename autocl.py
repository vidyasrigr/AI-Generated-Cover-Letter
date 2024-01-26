import streamlit as st
from openai import OpenAI
from PyPDF2 import PdfReader
import requests
from bs4 import BeautifulSoup
from difflib import SequenceMatcher
from dotenv import load_dotenv
import base64
import time
import os

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

additional_prompts = None 

def similarity(a, b):
    return SequenceMatcher(None, a, b).ratio()

def remove_duplicates(sentences):
    unique_sentences = []
    for sentence in sentences:
        # Check if a similar sentence is already present
        if not any(similarity(sentence.lower(), existing.lower()) > 0.8 for existing in unique_sentences):
            unique_sentences.append(sentence)
    return unique_sentences

def extract_text_from_url(url):
    try:
        # Fetch the HTML content of the webpage
        response = requests.get(url)
        response.raise_for_status()  # Check for a successful response

        # Parse HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')

        # Extract main content based on the specific structure of the webpage
        main_content = soup.find('main')  # Adjust based on your webpage structure

        # If 'main' tag is not present, extract text from the entire body
        if main_content is None:
            main_content = soup.body

        # Extract text content from the main content
        sentences = [tag.get_text(separator=' ', strip=True) for tag in main_content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'span', 'div', 'li', 'a', 'strong', 'em', 'b', 'i'])]

        # Remove duplicates
        unique_sentences = remove_duplicates(sentences)

        # Combine unique sentences into text content
        text_content = ' '.join(unique_sentences)

        return text_content

    except Exception as e:
        print(f"Error extracting text from URL: {e}")
        return None

def custom_spinner():
    my_bar = st.empty()
    for percent_complete in range(100):
        time.sleep(0.1)  # Simulate some processing time
        my_bar.progress(percent_complete + 1)
    my_bar.empty()

st.title("AI-Powered Cover Letter Generator")
st.markdown("""
                1. Enter URL for the job description or paste the job description.
                2. Upload your resume as PDF or paste contents of your resume.
                3. Add any additional requests you might have.
                4. Click generate and wait for AI to do its 🪄 magic!
                5. Review the generated cover letter and download it.
            """)

# Resume
resume_format = st.radio("Choose resume type", ('PDF', 'Paste'))
if resume_format == "PDF":
    resume_pdf = st.file_uploader("Upload your resume in PDF format")
    if resume_pdf:
        pdf_reader = PdfReader(resume_pdf)
        resume_text = ""
        for page in pdf_reader.pages:
            resume_text += page.extract_text()
else:  # Display text area only when "Paste" is chosen for resume
    if resume_format == "Paste":
        resume_text = st.text_area("Paste resume here", height=200)
    else:
        resume_text = ""  # Reset resume_text if "Upload" is chosen

# Job Description
jd_format = st.radio("Choose job description type", ('URL', 'Paste'))
if jd_format == "URL":
    jd_url = st.text_input("Enter Job Description URL")

    if jd_url:
        # Extract text content from the URL
        jd_text = extract_text_from_url(jd_url)
        
        # Display the extracted text
        if jd_text:
            success_message = "Information fetched from the URL successfully!"
            st.success(success_message)
        else:
            st.warning("Failed to extract text from the provided URL. Please check the URL.")

else:
    jd_text = st.text_input("Paste job description here")


# Additional Prompts
additional_request = st.radio("Would you like to add additional requests to the cover letter?", ('Yes, add prompts!', 'No, I leave it to AI!'))
if additional_request == "Yes, add prompts!":
    additional_prompts = st.text_area("Enter Additional Requests to customize your cover letter (One request per line)")

# Convert the user's additional_prompts input into a list of prompts
additional_prompt_list = additional_prompts.split('\n') if additional_prompts is not None else []

with st.form("input_form"):
    ai_temp = st.number_input("Enter creativity level", value = 0.9)
    submitted = st.form_submit_button("Generate Cover Letter")

if submitted:
    # Display spinner
    with st.spinner("Building your cover letter..."):
        custom_spinner()
        # RESUME SUMMARY
        # Create a conversation for the chat model with the extracted resume summary
        prompt_text = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"My resume : {resume_text}"},
            {"role": "assistant", "content": "You should give a concise summary of key information from my resume, in first person"},
            {"role": "user", "content": "In first paragraph mention my name, email ID, phone number."},
            {"role": "assistant", "content": "In second paragraph summarize my education qualification, coursework, skills"},
            {"role": "assistant", "content": "In third paragraph summarize my work experience and achievements, skills I obtained from work, and summary of my projects highlighting skills developed"}
        ]

        resume_summarization_response = client.chat.completions.create(model="gpt-3.5-turbo",
            messages = prompt_text,
            temperature=0.5,
            max_tokens=1000
        )

        # Extracted summary of the resume
        resume_summary = resume_summarization_response.choices[0].message.content

        # JD SUMMARY
        # Create a conversation for the chat model with the extracted jd summary
        jd_prompt_text = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": f"My Job Description : {jd_text}"},
            {"role": "assistant", "content": "You should give a concise summary of key information from the give job description"},
            {"role": "user", "content": "Mention the role name and company name."},
            {"role": "assistant", "content": "Give the main responsibilities of the job, educational requirements, skills, qualifications needed and any important information about the job."}
        ]

        jd_summarization_response = client.chat.completions.create(model="gpt-3.5-turbo",
            messages = jd_prompt_text,
            temperature=0.5,
            max_tokens=1000
        )

        # Extracted summary of the resume
        jd_summary = jd_summarization_response.choices[0].message.content


        # COVER LETTER GENERATOR
        # Create a conversation for the chat model with the extracted resume summary
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "assistant", "content": "You should generate a cover letter in first perso, with  based on the following resume content and the job description. Generate the response and include appropriate spacing between the paragraph text."},
            {"role": "user", "content": f"My resume : {resume_summary}"},
            {"role": "user", "content": f"Job description : {jd_summary}"},
            {"role": "user", "content": "The cover letter should be as concise as possible and no more than 5 paragraphs long. Do not include any subject."},
            {"role": "assistant", "content": "In the first paragraph focus on the following: name of the position and the company you are interested in, and why you think you are a great fit to the role."}, 
            {"role": "assistant", "content": "In one to two paragraphs concisely explain how the resume experience and skill align with the job's requirements and why you think you are a great fit to the role and a cultural fit for the company."}, 
            {"role": "assistant", "content": "In the last paragraph, mention that you are open to discuss further and provide contact information."},
            {"role": "assistant", "content": "The signature should only contain a close term and name, should not contain contact details."},
    {"role": "assistant", "content": "Sincerely,"},  
    {"role": "assistant", "content": "Name"}
        ]

        # Add additional prompts to the conversation
        for prompt in additional_prompt_list:
            messages.append({"role": "user", "content": f"Additional Prompt: {prompt}"})

        # Step 2: Generate the cover letter using the chat model
        generateCL = client.chat.completions.create(model="gpt-3.5-turbo",
            messages=messages,
            temperature=ai_temp,
            max_tokens=500
        )

        # Print the generated cover letter
        response = generateCL.choices[0].message.content
        
        # Display the generated cover letter with a success style
        st.success("Generated Cover Letter:")
        st.write(response)

        # Add a download link for the generated cover letter
        download_link = f'<a href="data:text/plain;base64,{base64.b64encode(response.encode()).decode()}" download="cover_letter.txt">Download Cover Letter</a>'
        st.markdown(download_link, unsafe_allow_html=True)