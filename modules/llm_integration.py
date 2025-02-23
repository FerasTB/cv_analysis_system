import os
import json
import logging
from flask import session
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# Load the API key from the environment variable.
groq_api = os.environ.get("GROQ_API_KEY")
if not groq_api:
    raise ValueError("GROQ_API_KEY is not set in the environment.")

# Initialize the Groq client with the API key.
client = Groq(api_key=groq_api)


def get_LLM_response(message):
    """
    Interact with the LLM model and get a response.
    Access the response using attribute notation.
    """
    messages = [
        {
            "role": "system",
            "content": "your response should only be in JSON format without any headers",
        },
        {
            "role": "user",
            "content": message,
        },
    ]

    logger.info("Sending message to LLM.")

    try:
        # Call the Groq client; note we access attributes, not dictionary keys.
        response = client.chat.completions.create(
            model="llama3-70b-8192", messages=messages, temperature=0
        )
        logger.info("Received response from LLM.")
        # Use attribute access to get the content from the first choice.
        return response.choices[0].message.content
    except Exception as e:
        logger.error("Error calling LLM: %s", e)
        raise e


def get_llm_response_from_history(message):
    """
    Interact with the LLM model using conversation history stored in the session.
    """
    # Load conversation history from session or initialize if absent.
    conversation_history = session.get(
        "conversation_history",
        [
            {
                "role": "system",
                "content": "your goal is to help the user about cvs query",
            }
        ],
    )

    # Append the user's message.
    conversation_history.append(
        {
            "role": "user",
            "content": message,
        }
    )

    logger.info(
        "Sending message to LLM with history (%d messages).", len(conversation_history)
    )

    try:
        # Call your LLM client using the full conversation history.
        response = client.chat.completions.create(
            model="llama3-70b-8192", messages=conversation_history, temperature=0
        )
        logger.info("Received response from LLM.")

        # Extract the assistant's reply.
        assistant_reply = response.choices[0].message.content

        # Append the assistant's reply to the conversation history.
        conversation_history.append(
            {
                "role": "assistant",
                "content": assistant_reply,
            }
        )

        # Save the updated conversation history back to the session.
        session["conversation_history"] = conversation_history
        session.modified = True
        return assistant_reply
    except Exception as e:
        logger.error("Error calling LLM: %s", e)
        raise e


def build_aggregated_cv_prompt(cv_records, additional_instructions=None):
    """
    Build a prompt that integrates multiple CV records and instructs the LLM to respond to queries about them.

    The prompt includes:
      - A summary of each CV with key details (personal information, education, work experience, skills, certifications).
      - Instructions for the LLM to answer queries such as:
          * Finding candidates with specific skills
          * Comparing education levels
          * Searching for experience in specific industries
          * Identifying matching candidates for job requirements

    Parameters:
      cv_records (list of dict): List of CV records, each containing keys like
        'personal_information', 'education_history', 'work_experience', 'skills', 'certifications'.
      additional_instructions (str, optional): Any extra instructions to append to the prompt.

    Returns:
      str: The aggregated prompt.
    """
    prompt_lines = []
    prompt_lines.append(
        "You are an expert data assistant with full access to a CSV file containing detailed information about candidates. The CSV includes fields such as candidate names, skills, education levels, work experiences, industries, and any other relevant job-related attributes."
    )
    prompt_lines.append("")
    prompt_lines.append(
        "The following are aggregated CV details from various candidates:\n"
    )

    for idx, record in enumerate(cv_records, start=1):
        prompt_lines.append(f"--- CV {idx} ---")
        prompt_lines.append(
            f"Personal Information: {record.get('personal_information', 'not mentioned')}"
        )
        prompt_lines.append(
            f"Education History: {record.get('education_history', 'not mentioned')}"
        )
        prompt_lines.append(
            f"Work Experience: {record.get('work_experience', 'not mentioned')}"
        )
        prompt_lines.append(f"Skills: {record.get('skills', 'not mentioned')}")
        prompt_lines.append(
            f"Certifications: {record.get('certifications', 'not mentioned')}"
        )
        prompt_lines.append("")

        prompt_lines.append("Your Task:")
        prompt_lines.append("Analyze the CSV and answer queries clearly and directly.")
        prompt_lines.append("")
        prompt_lines.append("Instructions:")
        prompt_lines.append("- Parse the CSV to extract candidate details.")
        prompt_lines.append(
            "- For skill queries (e.g., 'Who has Python?'), list candidates with and without the skill."
        )
        prompt_lines.append(
            "- For education queries, compare candidates’ education (degrees, institutions, etc.)."
        )
        prompt_lines.append(
            "- For industry queries, list candidates with relevant experience."
        )
        prompt_lines.append(
            "- For job matching, identify candidates meeting specified skills, education, and experience."
        )
        prompt_lines.append("")
        prompt_lines.append("Response Format:")
        prompt_lines.append("- Start with a brief summary.")
        prompt_lines.append("- Use bullet points or subheadings for clarity.")
        prompt_lines.append("- Keep responses concise and well-structured.")

    if additional_instructions:
        prompt_lines.append("")
        prompt_lines.append(additional_instructions)

    return "\n".join(prompt_lines)


def retry_llm_response(prompt, retries=3):
    """
    Retry getting an LLM response up to 'retries' times.
    Returns a valid JSON object if successful, otherwise None.
    """
    required_sections = [
        "Name",
        "Contact Information",
        "Professional Summary",
        "Experience",
        "Education",
        "Skills",
        "Certifications",
        "Languages",
    ]

    for attempt in range(retries):
        try:
            logger.info("Attempt %d to get LLM response.", attempt + 1)
            response_text = get_LLM_response(prompt)
            logger.info("LLM response text: %s", response_text)
            response_json = json.loads(response_text)

            # Validate that all required sections are present
            if all(section in response_json for section in required_sections):
                logger.info("LLM response validation passed.")
                return response_json
            else:
                logger.warning(
                    "Validation failed: Missing sections in attempt %d.", attempt + 1
                )
        except json.JSONDecodeError as json_err:
            logger.error(
                "Failed to parse LLM response to JSON in attempt %d: %s",
                attempt + 1,
                str(json_err),
            )
        except Exception as e:
            logger.error("Attempt %d failed: %s", attempt + 1, str(e))

    return None


def construct_cv_prompt(text):
    """
    Construct a prompt for the LLM that includes context from the extracted CV data.
    """
    prompt = f"""
Given the following text extracted from a CV:

'{text}'

Please extract the following sections from the CV and return them as structured JSON.

Important Instructions:

Use the exact key names as specified below, including capitalization and spacing.
Ensure that all keys in the JSON output match these exactly.
All dates should be in the format 'yyyy-mm-dd'.
If only the month and year are provided, use '01' as the day (e.g., 'June 2020' becomes '2020-06-01').
If only the year is provided, use '01-01' as the day and month (e.g., '2020' becomes '2020-01-01').
If any section is not found, return it as 'not mentioned'.
The JSON structure should include the following keys:

"Name" (String)
"Contact Information" (Object with keys: "email", "phone", "address")
"Professional Summary" (String)
"Experience" (Array of objects with keys: "title", "company", "start_date", "end_date", "description")
"Education" (Array of objects with keys: "degree", "institution", "start_date", "end_date", "description")
"Skills" (Array of strings)
"Certifications" (Array of objects with keys: "name", "issuing_organization", "issue_date", "expiration_date")
"Languages" (Array of strings)

Example JSON Structure:
{{
  "Name": "John Doe",
  "Contact Information": {{
    "email": "john.doe@example.com",
    "phone": "+1 555-1234",
    "address": "123 Main St, Anytown, USA"
  }},
  "Professional Summary": "Experienced software engineer with a focus on web development.",
  "Experience": [
    {{
      "title": "Software Engineer",
      "company": "Tech Solutions",
      "start_date": "2019-01-01",
      "end_date": "2023-10-01",
      "description": "Developed and maintained web applications using Python and Flask."
    }}
  ],
  "Education": [
    {{
      "degree": "B.Sc. in Computer Science",
      "institution": "State University",
      "start_date": "2013-09-01",
      "end_date": "2017-05-31",
      "description": "Graduated with honors."
    }}
  ],
  "Skills": ["Python", "Flask", "JavaScript", "SQL"],
  "Certifications": [
    {{
      "name": "AWS Certified Solutions Architect",
      "issuing_organization": "Amazon",
      "issue_date": "2020-03-01",
      "expiration_date": "2023-03-01"
    }}
  ],
  "Languages": ["English", "Spanish"]
}}
Please ensure that your JSON output matches this structure exactly.
    """
    return prompt


def get_cv_analysis(text):
    """
    Given extracted CV text, construct the prompt and call the LLM using retry logic.
    Returns a tuple: (response JSON or error message, status code).
    """
    prompt = construct_cv_prompt(text)
    response_json = retry_llm_response(prompt)

    if not response_json:
        logger.error("Failed to process the CV after multiple attempts.")
        return ({"error": "Failed to process the CV after multiple attempts."}, 500)

    return (response_json, 200)
