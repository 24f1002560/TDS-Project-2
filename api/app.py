import subprocess
import os
import textwrap
import logging
from flask import Flask, request, jsonify
from utils.question_matching import find_similar_question
from utils.file_process import unzip_folder
from utils.function_definations_llm import function_definitions_objects_llm
from utils.openai_api import extract_parameters
from utils.solution_functions import functions_dict


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


TMP_DIR = "tmp_uploads"
os.makedirs(TMP_DIR, exist_ok=True)

app = Flask(__name__)


SECRET_PASSWORD = os.getenv("SECRET_PASSWORD")

@app.route("/api/", methods=["POST"])
def process_file():
    """Handles incoming POST requests with a question and an optional file."""
    try:
        question = request.form.get("question")
        if not question:
            data = request.get_json()  # Try getting JSON data
            question = data.get("question") if data else None
        file = request.files.get("file") 

        if not question:
            return jsonify({"error": "Missing 'question' field"}), 400

        
        matched_function, matched_description = find_similar_question(question)
        logging.info(f"Matched function: {matched_function}")

        tmp_dir = TMP_DIR  
        file_names = []
        if file:
            tmp_dir, file_names = unzip_folder(file)

        
        function_definitions = function_definitions_objects_llm.get(matched_function, {})
        parameters = extract_parameters(str(question), function_definitions) or []

       
        solution_function = functions_dict.get(
            matched_function, lambda *args: "No matching function found"
        )

        
        answer = solution_function(*([file] if file else []) + parameters)

       
        formatted_answer = textwrap.dedent(str(answer)).strip()

        return jsonify({"answer": formatted_answer})

    except Exception as e:
        logging.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

@app.route("/redeploy", methods=["GET"])
def redeploy():
    """Triggers redeployment using a shell script, if the correct password is provided."""
    password = request.args.get("password")

    if password != SECRET_PASSWORD:
        return "Unauthorized", 403

    try:
        subprocess.run(["bash", "../redeploy.sh"], check=True)
        return "Redeployment triggered!", 200
    except subprocess.CalledProcessError as e:
        logging.error(f"Redeployment failed: {e}")
        return jsonify({"error": f"Redeployment failed: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)), debug=True)
