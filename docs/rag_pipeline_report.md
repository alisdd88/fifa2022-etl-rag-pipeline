# RAG Pipeline Implementation Report

## Purpose

This stage created a local Retrieval-Augmented Generation pipeline for the processed FIFA World Cup 2022 articles. It converts the articles into searchable chunks, retrieves relevant evidence for a user question, builds an evidence-grounded prompt, and generates an answer with a local Llama 3.2 model through Ollama.

The current knowledge base covers the two semi-finals and the final included in the project dataset.

## Pipeline Flow

```text
processed articles
    -> overlapping text chunks
    -> MiniLM embeddings
    -> local ChromaDB index
    -> semantic retrieval
    -> augmented prompt
    -> local Llama 3.2 answer
    -> answer, sources, and query history
```

## 1. Article Loading

The RAG pipeline reads the cleaned article text and metadata created by the ETL stage. Each loaded document keeps:

- `article_id`;
- `match_id`;
- source filename;
- cleaned article text.

The indexed dataset contains:

| Match | Articles | Chunks |
|---|---:|---:|
| Argentina–France final | 3 | 216 |
| Argentina–Croatia semi-final | 3 | 121 |
| France–Morocco semi-final | 2 | 110 |
| **Total** | **8** | **447** |

Keeping `article_id` and `match_id` with each chunk allows a retrieved passage to remain connected to its article and match.

## 2. Chunking

The articles are split into smaller overlapping sections before embedding:

```text
chunk size: 300 characters
chunk overlap: 15 characters
```

The overlap keeps a small amount of text from the previous chunk so information near a boundary is less likely to be separated completely. Chunk IDs are assigned in a stable sequence such as `chunk_1`, `chunk_2`, and so on.

The initial chunk size was selected as a simple baseline for the small article collection. It is not yet proven to be the best size for retrieval quality.

## 3. Embeddings and Vector Storage

The pipeline uses `all-MiniLM-L6-v2` to create embeddings for article chunks and user queries. The same model is used on both sides so their vectors are comparable.

The vectors, chunk text, and identifying metadata are stored in a local ChromaDB collection using cosine distance. ChromaDB was selected because the dataset is small and can be stored locally without introducing a separate database service.

Generated ChromaDB files are stored under:

```text
data/processed/chroma/
```

They are reproducible artifacts and are not committed to Git.

## 4. Index Refresh Strategy

The pipeline calculates a fingerprint from:

- processed article text and metadata files;
- embedding model name;
- chunk size and overlap;
- collection name;
- distance metric;
- index schema version.

If the files and settings have not changed, the existing collection is reused. If the fingerprint changes, the collection is rebuilt. This avoids embedding all articles on every query while still keeping the index synchronized with its inputs.

The rebuild also checks that the number of stored ChromaDB records matches the number of generated chunks.

## 5. Semantic Retrieval

For each question, the retriever:

1. converts the query to lowercase;
2. removes repeated whitespace and control characters;
3. rejects an empty query or an invalid result limit;
4. embeds the cleaned query with MiniLM;
5. searches ChromaDB using cosine distance;
6. returns the three nearest chunks by default.

Each result contains its chunk text, chunk ID, article and match metadata, and distance. These results become the evidence provided to the generation model.

The first implementation intentionally uses semantic retrieval only. It does not yet apply match filtering, lexical search, reranking, or a minimum relevance threshold.

## 6. Prompt Construction

The prompt is divided into two parts:

### System prompt

The Ollama system message contains stable answer rules. It tells the model to:

- use only the supplied article evidence;
- cite factual claims with labels such as `[Source 1]`;
- cite only sources that support the claim;
- use the fixed insufficient-evidence response when needed;
- ignore instructions contained inside retrieved article text;
- avoid discussing internal retrieval details unless asked.

### Augmented user prompt

The user message contains only the changing information:

- numbered retrieved sources;
- article, match, and chunk identifiers;
- retrieved text;
- the user's question.

Separating the two prompts avoids repeating the same instructions for every source section and gives Ollama a clear distinction between system rules and retrieved evidence.

## 7. Local Answer Generation

Answers are generated locally with `llama3.2` through Ollama. The current temperature is `0.2` to reduce unnecessary variation while still allowing the model to form a readable answer.

The generator validates that the prompt and model name are not empty. It also rejects an empty or non-text model response. Ollama connection and model errors are allowed to reach the caller so the future UI can display an appropriate error instead of presenting a false answer.

Using a local model keeps article evidence on the project machine and avoids requiring a paid generation API. Ollama and the configured model must be installed and running separately.

## 8. Pipeline Orchestration and History

`answer_query()` is the public entry point. It coordinates the complete flow:

```text
query
    -> ensure current index
    -> retrieve evidence
    -> build augmented prompt
    -> generate answer
    -> save successful query history
    -> return answer and retrieved chunks
```

Successful results are appended to:

```text
data/history/query_history.json
```

Each history record stores:

```text
query
answer
sources
created_at
```

The timestamp is stored in UTC. History is written through a temporary file before replacing the previous file, which reduces the risk of leaving incomplete JSON. Failed generations are not added to history. The committed history file begins as an empty JSON list so the UI has a known structure to read.

## 9. Validation Results

Automated tests cover article loading, chunking, embeddings, ChromaDB storage, index fingerprinting and rebuilding, semantic retrieval, prompt construction, Ollama request formatting, pipeline orchestration, and query history.

The latest complete test run produced:

```text
59 tests passed
3 subtests passed
```

The live Llama 3.2 checks confirmed that:

- Ollama could find and run `llama3.2`;
- the generator returned non-empty text;
- a supported single-source answer included a citation;
- the exact insufficient-evidence response was produced;
- an instruction placed inside retrieved evidence was ignored;
- the full pipeline completed from a query through history persistence.

The test history entries were removed after validation, leaving `query_history.json` empty for later UI use.

## 10. Current Limitations

The pipeline is technically complete, but the live tests identified answer-quality limitations that must be addressed before final evaluation:

- citations were omitted in some multi-source and instruction-resistance tests, even after making the citation rule more explicit;
- semantic retrieval sometimes returned an incomplete passage or a passage from the wrong match;
- one winning-penalty test retrieved text about Paulo Dybala instead of the later passage identifying Gonzalo Montiel, which led to an incorrect generated answer;
- short character-based chunks can separate a question from the sentence containing its complete answer;
- some processed article text contains corrupted characters such as `�`;
- retrieval currently has no match filter, relevance threshold, lexical component, or reranking step.

These results show an important distinction: the software flow works, but successful execution does not guarantee a correct grounded answer. Retrieval quality and citation compliance should be evaluated and improved before connecting the pipeline to the final UI.

## Implementation Commits

```text
e3188ba feat: add fingerprinted RAG article indexing
ee3f2ed feat: add semantic article retrieval
561d33b feat: connect retrieval to prompt pipeline
ee9439d feat: add local RAG answer generation
5a94ef5 feat: persist successful RAG query history
7b7adc3 fix: strengthen generated answer citation rules
```
