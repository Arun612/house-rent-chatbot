import json
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from config import GROQ_API_KEY, GROQ_LLM_MODEL
from pydantic import BaseModel, Field

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_LLM_MODEL,
    temperature=0.0,
)

class LeaseMetadata(BaseModel):
    rent_amount: str = Field(description="The monthly rent amount, e.g., '$1,500'. Return 'Not specified' if not found.")
    deposit_amount: str = Field(description="The security deposit amount, e.g., '$1,500'. Return 'Not specified' if not found.")
    lease_term: str = Field(description="The duration of the lease, e.g., '12 months' or 'Month-to-month'. Return 'Not specified' if not found.")
    pet_policy: str = Field(description="A brief summary of the pet policy, e.g., 'Pets allowed' or 'No pets allowed'. Return 'Not specified' if not found.")

def extract_metadata(document_text: str) -> dict:
    """Extracts key lease terms from the document text using Groq."""
    parser = JsonOutputParser(pydantic_object=LeaseMetadata)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert real estate paralegal. Extract the requested information from the lease agreement text.\n\n{format_instructions}"),
        ("human", "Lease Document Text:\n{text}")
    ])
    
    chain = prompt | llm | parser
    
    # Truncate to first ~8000 characters to save tokens/time and avoid context limits.
    # Essential terms are almost always on the first few pages.
    truncated_text = document_text[:8000]
    
    try:
        result = chain.invoke({
            "text": truncated_text,
            "format_instructions": parser.get_format_instructions()
        })
        return result
    except Exception as e:
        print(f"Metadata extraction failed: {e}")
        return {
            "rent_amount": "Extraction failed",
            "deposit_amount": "Extraction failed",
            "lease_term": "Extraction failed",
            "pet_policy": "Extraction failed"
        }
