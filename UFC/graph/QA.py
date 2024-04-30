import json
from openai import OpenAI
from falkordb import FalkorDB
from graph_schema import graph_schema
from dotenv import load_dotenv

load_dotenv()

def run_cypher_query(graph, query):
    try:
        results = graph.ro_query(query).result_set
    except:
        results = {"error": "Query failed please try a different variation of this query"}
    
    if len(results) == 0:
        results = {"error": "The query did not returned any data, please make sure you're using the right edge directions and you're following the correct graph schema"}

    return str(results)

def schema_to_prompt(schema):
    prompt = "The Knowledge graph contains nodes of the following types:\n"
    
    for node in schema['nodes']:
        lbl = node
        node = schema['nodes'][node]
        if len(node['attributes']) > 0:
            prompt += f"The {lbl} node type has the following set of attributes:\n"
            for attr in node['attributes']:
                t = node['attributes'][attr]['type']
                prompt += f"The {attr} attribute is of type {t}\n"
        else:
            prompt += f"The {node} node type has no attributes:\n"
    
    prompt += "In addition the Knowledge graph contains edge of the following types:\n"
    
    for edge in schema['edges']:
        rel = edge
        edge = schema['edges'][edge]
        if len(edge['attributes']) > 0:
            prompt += f"The {rel} edge type has the following set of attributes:\n"
            for attr in edge['attributes']:
                t = edge['attributes'][attr]['type']
                prompt += f"The {attr} attribute is of type {t}\n"
        else:
            prompt += f"The {rel} edge type has no attributes:\n"
        
        prompt += f"The {rel} edge connects the following entities:\n"
        for conn in edge['connects']:
            src  = conn[0]
            dest = conn[1]
            prompt += f"{src} is connected via {rel} to {dest}, (:{src})-[:{rel}]->(:{dest})\n"
    
    return prompt

def main():
    # Connect to FalkorDB
    db = FalkorDB(host='localhost', port=6379)
    g  = db.select_graph("UFC")
    
    schema = graph_schema(g)
    schema_prompt = schema_to_prompt(schema)
    
    client = OpenAI()

    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_cypher_query",
                "description": "Runs a Cypher query against the knowledge graph",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Query to execute",
                        },
                    },
                    "required": ["query"],
                },
            },
        }
    ]

    available_functions = {
        "run_cypher_query": run_cypher_query,
    }
    
    SYSTEM_MESSAGE = "You are a Cypher expert with access to a direcred knowledge graph\n"
    SYSTEM_MESSAGE += schema_prompt
    SYSTEM_MESSAGE += "Query the knowledge graph to extract relavent information to help you anwser the users questions, base your answer only on the context retrieved from the knowledge graph, do not use preexisting knowledge."
    SYSTEM_MESSAGE += """For example to find out if two fighters had fought each other e.g. did Conor McGregor every compete against Jose Aldo issue the following query: MATCH (a:Fighter)-[]->(f:Fight)<-[]-(b:Fighter) WHERE a.Name = 'Conor McGregor' AND b.Name = 'Jose Aldo' RETURN a, b\n"""
  
    # Send the conversation and available functions to the model
    messages = [{"role": "system", "content": SYSTEM_MESSAGE}]
    
    while True:
        question = input("How can I help you with?\n")
        messages.append({"role": "user", "content": question})
        
        # Call the function
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=messages,
            tools=tools,
            tool_choice="auto",  # auto is default, but we'll be explicit
        )

        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        # Check if the model wanted to call a function
        if tool_calls:
            #print(f"response_message: {response_message}")
            messages.append(response_message)  # extend conversation with assistant's reply

            # Send the info for each function call and function response to the model
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                assert(function_name == "run_cypher_query")
                function_args = json.loads(tool_call.function.arguments)
                function_response = run_cypher_query(g, function_args.get("query"))
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )
            
            # extend conversation with function response
            second_response = client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=messages,
            )  # get a new response from the model where it can see the function response

            messages.append({"role": "assistant", "content": second_response.choices[0].message.content})
            print(f"\n{second_response.choices[0].message.content}\n")

if __name__ == "__main__":
    main()
