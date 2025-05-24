# 防災対策学習サイト (Disaster Preparedness Learning Site)

This project is a web application designed to help users learn about disaster preparedness. It includes a stockpile simulator to calculate necessary emergency supplies and an AI-powered chat assistant for answering questions related to disaster safety and preparedness based on provided documents.

## Features

### 1. 防災備蓄シミュレータ (Disaster Stockpile Simulator)
- **User Input:** Allows users to input the number of family members categorized by age groups:
    - 成人 (Adult)
    - 子供(中学生以上) (Child - Junior high school and older)
    - 子供 (Child - Younger, elementary school and below)
    - 乳幼児 (Infant)
    - 高齢者 (Elderly)
- **System Output:** Calculates and displays the necessary stockpile items (food, hygiene products, essentials) required for both a minimum of 3 days and a recommended 7 days. Results are presented in a table, grouped by item category. The data for these calculations is sourced from an external CSV file (`data/stockpile_items.csv`).

### 2. 防災Chat (Disaster Chat)
- **User Input:** Users can ask questions related to disaster preparedness in a chat interface (e.g., "What should I do during an earthquake?").
- **System Output:** An AI assistant, powered by a RAG (Retrieval Augmented Generation) system using Google's Gemini-Flash model via Langchain, answers questions. The AI's knowledge is based on information extracted from PDF documents provided by the user/administrator in the `documents/` folder. When providing an answer, the chat also lists the source documents (filename and page number) that contributed to the response.

## Tech Stack

- **Backend:**
    - Language/Framework: Python (Flask)
    - Key Libraries: Langchain (v0.3.x for RAG), langchain_community, langchain_google_genai, pypdf, faiss-cpu, python-dotenv, pytest
- **Frontend:**
    - Library/Framework: React (using Create React App structure)
    - Key Libraries: react-router-dom
- **AI Model:** Google Gemini-Flash (accessed via `langchain_google_genai`)
- **Data Storage:**
    - Stockpile Items Data: Managed via a CSV file (`disaster_prep_site/data/stockpile_items.csv`).
    - RAG Vector Store: FAISS (index stored in `disaster_prep_site/backend/vectorstore_faiss/`).
- **Containerization:** Docker, Docker Compose
- **Web Server (Frontend):** Nginx (serving the React build and proxying API requests in the Docker setup)

## Prerequisites

- **Docker and Docker Compose:** Must be installed on your system. Visit the [official Docker website](https://www.docker.com/get-started) for installation instructions.
- **Google API Key:** A Google API Key with access to the Gemini API (specifically, the "Generative Language API") is required for the Disaster Chat feature to function. You can obtain this from the [Google Cloud Console](https://console.cloud.google.com/).

## Setup and Running the Application

1.  **Clone the Repository / Prepare Files:**
    - If you've cloned this repository, you're all set.
    - Otherwise, ensure all project files are present in a root directory (e.g., `disaster_prep_site/`).

2.  **Configure Environment Variables (Google API Key):**
    - Navigate to the `disaster_prep_site/backend/` directory.
    - Create a file named `.env`. You can copy `backend/.env.example` if it exists, or create a new file.
    - Add your Google API Key to the `.env` file. It should look like this:
      ```env
      GOOGLE_API_KEY="YOUR_ACTUAL_GOOGLE_API_KEY_HERE"
      ```
    - **Important:** Replace `"YOUR_ACTUAL_GOOGLE_API_KEY_HERE"` with your real Google API Key. Without a valid API key, the Disaster Chat feature will not initialize correctly and will return an error message.

3.  **Prepare Stockpile Data (Optional Customization):**
    - The list of stockpile items and their recommended quantities is managed in `disaster_prep_site/data/stockpile_items.csv`.
    - You can edit this CSV file to add, remove, or modify items to suit different regional needs or updated guidelines. The backend will load this data on startup.

4.  **Add PDF Documents for RAG System:**
    - Place any PDF documents that the Disaster Chat should use as its knowledge base into the `disaster_prep_site/documents/` folder. These could be official government disaster preparedness guides, local emergency plans, etc.
    - **Note on First Run / Document Changes:**
        - When the application starts for the first time, or if the `disaster_prep_site/backend/vectorstore_faiss/` directory is empty or deleted, the RAG system will process all PDFs in the `documents/` folder to build its vector store.
        - This processing can take some time, depending on the number and size of the PDF documents.
        - Subsequent startups will be much faster as they will load the pre-built vector store from `backend/vectorstore_faiss/`.
        - If you add, remove, or change PDF documents in the `documents/` folder, you should delete the `backend/vectorstore_faiss/` directory to force the system to rebuild the vector store with the updated content on the next run.

5.  **Build and Run with Docker Compose:**
    - Open a terminal or command prompt.
    - Navigate to the root directory of the project (i.e., the `disaster_prep_site/` directory).
    - Run the following command:
      ```bash
      docker-compose up --build
      ```
    - This command will:
        - Build the Docker images for the backend and frontend services (if they don't exist or if Dockerfiles have changed).
        - Start the containers for both services.
    - Wait for the build process and service startup to complete. You will see logs from both services in your terminal.

6.  **Accessing the Application:**
    - **Frontend Application:** Open your web browser and navigate to `http://localhost:3000`.
    - **Backend API Endpoints (Optional, for direct testing with tools like Postman or curl):**
        - Stockpile Simulator: `POST http://localhost:5001/api/stockpile_simulator`
          - Example Payload: `{"family_members": {"adult": 2, "child": 1}}`
        - Disaster Chat: `POST http://localhost:5001/api/chat`
          - Example Payload: `{"question": "What to do in an earthquake?"}`

## Development Notes

### Running Tests
To run the backend unit tests, ensure the Docker services are running (or at least the backend service if testing in isolation with a separate command). Then, execute the following command in a new terminal from the project root directory:
```bash
docker-compose exec backend pytest -v
```
This command runs `pytest` inside the `backend` service container. The `-v` flag provides verbose output. The tests are located in `disaster_prep_site/backend/tests/`.

### Project Structure
A brief overview of the main directories:
- `disaster_prep_site/`
    - `backend/`: Contains the Python Flask backend application.
        - `app/`: Core application logic, including `main.py` (API endpoints) and `rag_logic.py`.
        - `tests/`: Unit tests for the backend (e.g., `test_stockpile_simulator.py`, `test_rag_logic.py`).
        - `vectorstore_faiss/`: Stores the FAISS vector index for the RAG system. This is created automatically if it doesn't exist and `documents/` are present.
        - `.env`: Stores the `GOOGLE_API_KEY` (you need to create this file).
        - `Dockerfile`: Instructions for building the backend Docker image.
        - `requirements.txt`: Python dependencies.
    - `frontend/`: Contains the React frontend application.
        - `public/`: Static assets and `index.html`.
        - `src/`: React components, pages, CSS, and application logic.
        - `nginx.conf`: Nginx configuration used within the frontend Docker container to serve the React app and proxy API requests.
        - `Dockerfile`: Instructions for building the frontend Docker image (multi-stage build).
        - `package.json`: Frontend dependencies and scripts.
    - `data/`: Contains external data files.
        - `stockpile_items.csv`: CSV file defining items for the stockpile simulator.
    - `documents/`: Directory for storing PDF documents that the RAG system will use as its knowledge base.
    - `docker-compose.yml`: Docker Compose file to define and run the multi-container application (backend and frontend).
    - `README.md`: This file, providing project documentation.

---
This README provides a comprehensive guide for setting up, running, and understanding the Disaster Preparedness Learning Site.
