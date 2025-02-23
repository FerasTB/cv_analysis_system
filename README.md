# CV Analysis & Chatbot System

A robust system for processing PDF/Word CVs, extracting key information using OCR and prompt engineering, and providing a user-friendly chatbot interface for querying multiple CVs.

## Overview

This project enables you to effortlessly upload and process CVs in PDF or Word format. The system automatically handles scanned documents with OCR, integrates with large language models (LLMs) for natural language processing, and offers an intuitive chatbot interface for detailed queries.

## Features

### Document Processing
- **Multi-format Support:** Processes both PDF and Word documents.
- **Scanned PDF Detection:** Automatically detects scanned PDFs and extracts text using OCR.
- **Image Conversion:** Converts PDF pages to images as needed before performing OCR.

### LLM Integration
- **Service Integration:** Works with [Groq](https://pypi.org/project/groq/) or alternative LLM services.
- **Prompt Engineering:** Utilizes prompt engineering techniques and maintains conversation history.
- **Robust Error Handling:** Manages API errors and rate limits efficiently.

### Query Chatbot
- **User Interface:** Offers a front-end chat UI for seamless user interactions.
- **Context Management:** Supports follow-up questions through effective conversation context management.

## Setup Instructions

### 1. Clone or Fork the Repository

Clone the repository to your local machine:

```bash
git clone https://github.com/FerasTB/cv_analysis_system.git
cd cv_analysis_system
```
### 2. Create and Activate a Virtual Environment

It is recommended to use a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```
(On Windows: use venv\Scripts\activate)
### 3. Install Dependencies

Install the required packages:

```bash
pip install -r requirements.txt
```
Note: Ensure that Tesseract and Poppler are installed on your system if you require OCR and PDF conversion capabilities.
### 4. Set Up Environment Variables

Rename *bash .env.example* to *.env* and provide valid values for the environment variables. For example:


```bash
GROQ_API_KEY="your_groq_api_key"
DEBUG=True
```
### 5. Initialize the Database (Optional)

If your application uses a local SQLite database to store CV data, initialize or reset it as follows:

```bash
python
>>> from modules.cv_parser import init_db
>>> init_db()
>>> exit()
```
This will create (or reset) the local SQLite database file.

### 6. Start the Server

Run the server using the following command:

```bash
python run.py
```
By default, this starts a Flask server accessible at http://127.0.0.1:5000.

### 7. Open the Chatbot Interface

- Open your web browser and navigate to http://127.0.0.1:5000/chatbot.
- Use the Chat tab to interact with the chatbot.
- Use the Upload CV tab to submit PDF or Word documents.

## Testing

The project uses pytest for testing. Run tests from the project root using:


```bash
pytest
```


