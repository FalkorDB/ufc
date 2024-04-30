import os
from openai import OpenAI
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

def main():
    client = OpenAI()
    
    pc = Pinecone(api_key=os.getenv("PINECONE_TOKEN"))
    index = pc.Index("ufc")

    SYSTEM_MESSAGE = "You're a helpful assistance, base your answer only on the provided context, do not use preexisting knowledge."
  
    # Send the conversation and available functions to the model
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}]

    while True:
        question = input("How can I help you with?\n")
        
        # Create embeddings from user question
        response = client.embeddings.create(
            input=question,
            model="text-embedding-3-small"
        )
        vec = response.data[0].embedding
        
        # Query vector DB for similar documents
        response = index.query(vector=vec, top_k=10, include_values=False, includeMetadata=True)

        matches = response['matches']

        context = []
        for match in matches:
            context.append(match['metadata'])

        content = f"Please use this context: {context}\n To answer the following question: {question}."
        messages.append({"role": "user", "content": content})

        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages
        )

        response_message = response.choices[0].message
        
        # extend conversation with assistant's reply
        messages.append(response_message)

        print(f"\n{response_message.content}\n")

if __name__ == "__main__":
    main()
