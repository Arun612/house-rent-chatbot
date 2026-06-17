# RentChat 🏠

An intelligent AI-powered chatbot designed to help you interact with housing rental agreements and leases. Built with **FastAPI**, **LangChain**, **Pinecone**, and a modern **React/Vite** frontend.

## Features
- **Document Upload:** Upload any PDF lease or rental agreement. The backend uses PyMuPDF and LangChain to chunk and index the text.
- **RAG Architecture:** Embeds document chunks into a Pinecone vector database using HuggingFace sentence-transformers.
- **AI Chat:** Uses Groq's high-speed LLMs to answer questions precisely based *only* on the provided context.
- **Source Citations:** The UI shows you exactly which page and paragraph the AI used to answer your question.
- **Beautiful UI:** A premium, light-themed React frontend with smooth animations and instant state updates.

## Tech Stack
- **Backend:** Python, FastAPI, LangChain, Pinecone DB, Groq
- **Frontend:** React, Vite, Lucide Icons

## Setup

### 1. Environment Variables
Create a `.env` file in the `backend/` directory:
```env
GROQ_API_KEY=your_groq_api_key_here
PINECONE_API_KEY=your_pinecone_api_key_here
```

### 2. Start the Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 3. Start the Frontend
```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.
