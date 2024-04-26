# ufc
UFC Knowledge graph demo

# Introduction
This demo inlustrates two alternative to building RAG Q&A AI agent over the [UFC stats dataset](https://www.kaggle.com/datasets/rajeevw/ufcdata)
One uses a Knowledge Graph the other uses a Vector DB

# Data
The [UFC](http://ufc.com) publicly offers statistics for each fight it held in addition to individual figher's
personal statistics on [UFC stats](http://ufcstats.com/statistics/events/completed)

This information includes among other details:
* Where and when an event was held
* Details and statistics of a fight
* Who won a fight
* How long was a fight
* Fighter's reach

# Querying the AI agent
Once the data is loaded either into a Knowledge Graph or into a Vector DB
users can start asking the AI agent questions, for example:

```
Which fighter holds the fastest win?

The fighter who holds the fastest win is Jorge Masvidal, with a win in just 5 second

Who did he win against ?

Jorge Masvidal won against Ben Askren in the fight where he secured the fastest win.

List fighters who had a trilogy match

The only fighters specifically identified in the data having a trilogy (i.e., three matches against the same opponent) are:

- Frankie Edgar and BJ Penn
- Randy Couture and Vitor Belfort
- BJ Penn and Frankie Edgar
- Cain Velasquez and Junior Dos Santos
...
```

# Running the demo

Install Python modules
```sh
pip install -r requirements.txt
```

## Graph
### Prerequisites

Run FalkorDB
```sh
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:edge
```

Create the Knowledge Graph
from the UFC/graph folder run
```sh
python ingest.py
```

Run the QA agent
```
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
python QA.py
```

## Vector
### Prerequisites
Create vector index, in this demo we'll be using [Pinecode](https://www.pinecone.io)
The process of indexing the data can take about 15 minutes as we're creating ~10K vector embeddings and indexing them.

From the UFC/vector folder run
```
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
export PINECONE_TOKEN="YOUR_PINECONE_TOKEN"
python ingest.py
```

Run the QA agent
```
python QA.py
```

# Results
From our experiments the knowledge graph version managed to generate much more accurate answers
using less tokens, this can be attributed to a number of reasons:

1. Because Knowledge graph follow a certian schema the LLM has good understanding of the data available
unlike vector index where the concept of a schema doesn't exists.

2. The Module has access to the entire knowledge base via a well established query language (Cypher)
Where with Vector DB the model is limited to K (in our case 10) documents which are semanticly similar to the user's question

3. In cases where the user question isn't sementicly similar to a possible answer,
the chances for the modle to generate a decent answer are slim.
Alowing the LLM to generate a context retrival query for each user question increases the chances for the model to recieve
relavent context for a given question.

4. Questions requiering access to large portion of the data e.g. how many fights were held by the UFC ?
or Which fighter has most wins? can't be answered using the Vector DB approach as this one is limited to a set of documents
similar to the user question. On the other hand, when using a Knowledge Graph the LLM is able to compose a query which will
perform the neccessery aggregations and it is able to use the query result to compose its final answer.
