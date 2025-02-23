import sys
import os

# Add the project root directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Blueprint, render_template, request, jsonify, session
from modules.llm_integration import (
    get_llm_response_from_history,
    build_aggregated_cv_prompt,
)
from modules.cv_parser import process_and_save_cv, get_all_cv_data
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
chat_bp = Blueprint("chat", __name__)


@chat_bp.route("/chatbot")
def chatbot_interface():
    return render_template("chatbot.html")


@chat_bp.route("/send_message", methods=["POST"])
def send_message():
    try:
        data = request.get_json()
        message = data.get("message", "").strip()
        if not message:
            return jsonify({"error": "Empty message"}), 400

        # Retrieve conversation history from session or initialize it.
        conversation_history = session.get(
            "conversation_history",
            [
                {
                    "role": "system",
                    "content": "your goal is to help the user about cvs query",
                }
            ],
        )

        # Retrieve all CV records and build aggregated CV context.
        cv_records = get_all_cv_data()
        logger.info("Retrieved %d CV records.", len(cv_records))
        if cv_records:
            aggregated_prompt = build_aggregated_cv_prompt(cv_records)
            # Only add the CV context if it hasn't been added already.
            if not any(
                msg.get("role") == "system"
                and msg.get("content", "").startswith("CV Context:")
                for msg in conversation_history
            ):
                conversation_history.append(
                    {"role": "system", "content": "CV Context: " + aggregated_prompt}
                )
                logger.info("Added CV context to conversation history.")
        else:
            logger.info("No CV records available; skipping CV context.")

        # Save the updated conversation history back into the session.
        session["conversation_history"] = conversation_history
        session.modified = True
        # Get the LLM response using the updated conversation history.
        answer = get_llm_response_from_history(message)
        return jsonify({"answer": answer})
    except Exception as e:
        logger.error("Error in send_message: %s", e)
        return jsonify({"error": str(e)}), 500


@chat_bp.route("/upload_cv", methods=["POST"])
def upload_cv():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    try:
        cv_data = process_and_save_cv(file, file.filename)
        return jsonify(
            {"message": "CV uploaded and processed successfully.", "cv_data": cv_data}
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
