import os
from typing import Tuple

import openai
from burr.core import ApplicationBuilder, State, default, expr, Application
from burr.core.action import action
from burr.tracking import LocalTrackingClient
import uuid
import pinecone


# --- helper functions

def set_inital_chat_history() -> list[dict]:
    SYSTEM_MESSAGE = ("You're a helpful assistance, base your answer only on the provided context, "
                      "do not use preexisting knowledge.")

    messages = [{"role": "system", "content": SYSTEM_MESSAGE}]
    return messages

# --- actions

@action(
    reads=[],
    writes=["question", "chat_history"],
)
def human_converse(state: State, user_question: str) -> Tuple[dict, State]:
    """Human converse step -- make sure we get input, and store it as state."""
    new_state = state.update(question=user_question)
    new_state = new_state.append(chat_history={"role": "user", "content": user_question})
    return {"question": user_question}, new_state


@action(
    reads=["question", "chat_history"],
    writes=["chat_history", "vector"],
)
def extract_embedding(state: State, client: openai.Client) -> tuple[dict, State]:
    """AI step to create the text embedding."""
    question = state["question"]
    # Create embeddings from user question
    response = client.embeddings.create(
        input=question,
        model="text-embedding-3-small"
    )
    vector = response.data[0].embedding
    new_state = state.update(vector=vector)
    return {"usage": response.usage.to_dict()}, new_state


@action(
    reads=["vector", "chat_history", "question"],
    writes=["vector", "chat_history"],
)
def query_vectordb(state: State, vector_db_index: pinecone.Index, top_k: int = 20) -> Tuple[dict, State]:
    """Query the vector DB to create the message context."""
    vector = state["vector"]
    question = state["question"]
    response = vector_db_index.query(vector=vector,
                                     top_k=top_k,
                                     include_values=False,
                                     includeMetadata=True)
    matches = response['matches']
    context = []
    for match in matches:
        context.append(match['metadata'])
    content = f"Please use this context: {context}\n To answer the following question: {question}."
    new_state = state.append(chat_history={"role": "user", "content": content})
    new_state = new_state.update(vector=None)
    return {"num_results": len(response['matches'])}, new_state


@action(
    reads=["chat_history"],
    writes=["chat_history"],
)
def AI_generate_response(state: State, client: openai.Client) -> tuple[dict, State]:
    """AI step to generate the response."""
    messages = state["chat_history"]
    response = client.chat.completions.create(
        model="gpt-4-turbo-preview",
        messages=messages,
    )  # get a new response from the model where it can see the function response
    response_message = response.choices[0].message
    new_state = state.append(chat_history=response_message.to_dict())
    return {"ai_response": response_message.content,
            "usage": response.usage.to_dict()}, new_state


def build_application(
        db_client: pinecone.Pinecone,
        index_name: str,
        application_run_id: str,
        openai_client: openai.OpenAI) -> Application:
    """Builds the application."""
    # get the index to query
    index = db_client.Index(index_name)
    # set the initial chat history
    base_messages = set_inital_chat_history()

    tracker = LocalTrackingClient("ufc-pinecone")
    # create graph
    burr_application = (
        ApplicationBuilder()
        .with_actions(  # define the actions
            extract_embedding.bind(client=openai_client),
            query_vectordb.bind(vector_db_index=index),
            AI_generate_response.bind(client=openai_client),
            human_converse
        )
        .with_transitions(  # define the edges between the actions based on state conditions
            ("human_converse", "extract_embedding", default),
            ("extract_embedding", "query_vectordb", default),
            ("query_vectordb", "AI_generate_response", default),
            ("AI_generate_response", "human_converse", default)
        )
        .with_identifiers(app_id=application_run_id)
        .with_state(  # initial state
            **{"chat_history": base_messages, "tool_calls": []},
        )
        .with_entrypoint("human_converse")
        .with_tracker(tracker)
        .build()
    )
    return burr_application


if __name__ == '__main__':
    print("""Run 
    > burr 
    in another terminal to see the UI at http://localhost:7241
    """)
    _client = openai.OpenAI()
    _pinecone_client = pinecone.Pinecone(api_key=os.getenv("PINECONE_TOKEN"))
    _index_name = "ufc"
    _app_run_id = str(uuid.uuid4())  # this is a unique identifier for the application run
    # build the app
    _app = build_application(_pinecone_client, _index_name, _app_run_id, _client)

    # visualize the app
    _app.visualize(
        output_file_path="ufc-burr", include_conditions=True, view=True, format="png"
    )

    # run it
    while True:
        question = input("What can I help you with?\n")
        if question == "exit":
            break
        action, _, state = _app.run(
            halt_before=["human_converse"],
            inputs={"user_question": question},
        )
        print(f"AI: {state['chat_history'][-1]['content']}\n")
