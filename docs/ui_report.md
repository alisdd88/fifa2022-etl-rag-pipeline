# User Interface

## Purpose

The user interface provides a simple way to ask questions about the selected FIFA World Cup 2022 matches and review previous questions. It is built with Streamlit and connects directly to the existing RAG pipeline.

## Ask Page

The Ask page is the main page of the application. The user enters a question and selects **Get answer**.

The system then:

1. searches the processed articles for relevant information;
2. generates an answer using the local language model;
3. displays the question, answer, and supporting sources.

If the question is empty, the interface asks the user to enter a question. If the answer cannot be generated, an error message is shown instead of stopping the application.

## Answer Preview

Every result is displayed using the same answer preview. It contains:

- the original question;
- the generated or stored answer;
- the article sources used as evidence.

A **New Question** button returns the user to the Ask page and clears the previous question from the input field.

## History Page

Successful questions are already stored in:

```text
data/history/query_history.json
```

When valid history records exist, the interface shows a **History** navigation option. The History page lists previous questions with their date and time when available. It does not show complete answers in the list.

Selecting a question opens it in the same answer preview used for newly generated responses. This keeps the presentation of new and previous answers consistent.

If the history file is empty, invalid, or cannot be read, the History option is hidden. The user therefore does not see an empty or broken History page.

## Running the Interface

The interface can be started from the project directory with:

```text
streamlit run app.py
```

Ollama and the configured local model must be available to generate new answers. Previously stored history can still be viewed from the History page without generating another answer.
