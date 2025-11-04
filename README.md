# RAG Application - Project Documentation

## Overview

This repository contains a compplete RAG (Retrieval-Augmented Generation) application with web scraping capabilities, embedding processing and storage, and query functionality. The Web UI is a convenient interface for user to enter queries to the RAG application. Of course, the questions shall be specifically related to the contents you scraped off the web, otherwise, there is no point of having a RAG application; You can just qeury llm directly.

## Key Features

- __Web Scraping, Embedding, and Vector Storage__: Extract starting from any website url, process/embed text, and store content and embedding in local postgresql database.

- __Query Interface__: Support for natural language queries with domain-specific knowledge retrieved from scraped contents.

- __Web Interface__: Web-based UI for interaction with streaming response.

## Project Structure

```javascript
${basedir}/scraper/
├── .env                    # Environment configuration file
├── query_china_tollroads.py # Test vector query
├── requirements.txt       # Python dependencies
├── web_app.py            # Main web application
├── env/                  # Virtual environment
├── scraper/              # Core scraping functionality
└── static/              # Web server static files
```

## Getting Started

### Prerequisites

- Python 3.12 or higher

- pip (Python package manager)

- Virtual environment tools

- Postgresql@18 + pgvector extension 0.8.1

- An account/API key to use LLM. You can have a free account to use a free LLM model at OpenRouter.

### Database set up
I have everything set up on my macbook, if you are a windows user, please find the installation procedure on the web.

1. Postgresql database 18.0 installation
```
   brew search postgresql
   brew install postgresql@18
```
2. pgvector extension 0.8.1 installation
```
   brew install pgvector
```
3. link pgvector extension to Postgresql installation
   ```
   This works on Macbook:

   ln -s /usr/local/Cellar/pgvector/0.8.1/share/postgresql@18/extension/*  /usr/local/Cellar/postgresql@18/18.0/share/postgresql/extension/

   On Windows, you need to find the place pgvector is installed, and link the contents of extensions directory or copy them to the extension directory of your postgresql 18.0 installation.
   ```
4. Hard coded setup:
   ```
   database: "myprojdb"
   host:     "localhost"
   port:     5432
   schema:   "scraper"
   table:    "pages"
   user:     "myuser" 
   password  "mypassword"

   user myuser shall be the owner of myprojdb with full admin + R/W permissions
    ```
5. verify pgvector is supported in your db.
   ```
   To enable authentication on your db, edit /usr/local/var/postgresql@18/pg_hba.conf, change the 'trust' to 'md5' for your db connection from localhost or remote.

   login to your db:  psql -U myuser -d myprojdb

   run 'set search_path to scraper, public;'
   run 'create extension vector;'
   you shall see CREATED or ERROR: extension "vector" already exists if you run more than once.

   you can also do \dx to see installed extensions. it shall have vector (0.8.1)

   you can optionally create the pages table (the program shall create it automatically if not there)

   table "pages"" columns:

   id integer
   url text
   title text
   content text
   embedding vector(384)
   chunk_id integer

   pages_pkey is id
   pages_url_chunk_id is unique key
   ```
### Configuration

- __LLM model/Database interaction__: `.env` 
   ```
   PGVECTOR_DB_URL=postgresql://myuser:mypassword@localhost:5432/myprojdb OPENROUTER_API_KEY=sk-or-v1-7256xxxxxx DEEPSEEK_FREE_MODEL=deepseek/deepseek-chat-v3.1:free TOKENIZERS_PARALLELISM=false
   ```
- __Scraper/Spider Configuration__: settings.py
- __Dependencies__: `requirements.txt` 

### LLM Vendor Account and LLM Model

I recommend setting up an account at https://openrouter.ai/ and get an API key (sk-or-v1-7256.....).  The benefit of having an openrouter account is that it supports all major LLM models without the need to register with different model vendors and have a separate API key with each.  One openrouter API key let you have access to any models you choose, and openrouter handles the billing and payment of your usage. There are free LLM models you can configure via openrouter, and you pay nothing if you chooose to use one of the free models. I have configured deepseek/deepseek-chat-v3.1:free for this project.

### Environment (.env)

PGVECTOR_DB_URL=postgresql://myuser:mypassword@localhost:5432/myprojdb
OPENROUTER_API_KEY=sk-or-v1-7256xxxxxx
DEEPSEEK_FREE_MODEL=deepseek/deepseek-chat-v3.1:free
TOKENIZERS_PARALLELISM=false

### Application Installation

1. __Navigate to project directory__:
   ```
   git clone ....

   cd ${basedir}/scraper
   ```
2. __Set up virtual environment__:
   ```bash
   python -m venv env
   pip install -r requirements.txt

   source env/bin/activate
   ```

### Running the Application

- __Scraping/Embedding/Store__: 
   ```
   For scraping web content, Spider is used respecting rate limit and bot scrawler policies of the site.

   The configuration for the scraper is in the settings.py file. You can adjust the settings to fit your own preference. Two configuration items are of particular importance as listed below:

   DEPTH_LIMIT = 1
   CLOSESPIDER_PAGECOUNT = 500

   What they mean is that we will only crawl one level deep, and we stop scrawling after roughly around 500 urls if they are enough depth one referenced urls from the starting page. You can adjust either one or both to get the amount of data you are comfortable with in your local database. 

   You can crawl with a different starting urls with multiple runs. You can repeat the crawling of the same starting url more than once, but the data shall be saved only once as the data base has constraints to prevent duplicate data being saved twice.

   For scraping web site content, embedding, and save, run the following: 

   export SCRAPY_SETTINGS_MODULE=scraper.settings

   cd ${basedir}/scraper

   python -m scraper.embed_and_store {url}

   e.g. url = "https://en.wikivoyage.org/wiki/Driving_in_China"

   you should see some records stored in pages table while this is running.

   run below sql to verify:

   select count(*) from scraper.pages;

   Note on embedding:

   We are using the embedding model all-MiniLM-L6-v2, which has dimension of 384. You can try other embedding models with higher dimensions for potentially better result. For this demo project, it is good enough to serve the purpose.

   Since each page could be arbitarily long, we use 1500 character chuns (about 300 words) for each embedding; a url (page) usually have multiple chunks. Our vector search is on page chunks, not on a page as a whole.

   Note on vector operator:

   v1 <=> v2 is defined as:
   ```
   $$\text{cosineDistance}(v_1, v_2) = 1 - \cos(\theta) = 1 - \frac{v_1 \cdot v_2}{\|v_1\| \|v_2\|}$$
   ```
   Range: [0, 2]
   0 = perfect match (cos(θ) = 1)
   1 = orthogonal
   2 = opposite

   KNN vector search is based on cosine distance, meaning the smaller the distance, the closer the vectors are.

   SELECT id, url, title, content
        FROM pages
        ORDER BY embedding <=> %s::vector
        LIMIT 3;
   ```
- __Vector Search Query Testing__:

   ```
   This verification step is not needed for the RAG application to function, but it was an intermediary stage before integrating with a web UI during development. You can skip this and go directly with the web UI.

   python adhoc_query.py {your query}

   Your query shall be related to your scraped contents. e.g. use "what is the max speed limit on Expressway in China?" or "what is the max speed of bullet train in Chain?" for {your query}
 
   you should see 3 top records returned back.
   ```

- __Using the Web UI__:
   ```
   start FAST API server in ${basedir}/scraper

   uvicorn web_app:app --reload --port=8080

   then open in browser:

   http://localhost:8080
   ```

## Artifacts/Screen Shots

Below are some screen shots showing database set up, WEB UI of the RAG application, and some sample query results, both from the RAG UI and the verification from the database.

1. Database table "pages":

   ![data base table](static/img/pages-table.png)

2. WEB UI:

   ![Rag Web UI](static/img/RAG-UI.png)

3. Scraped content vs RAG answers:
   ```
   Following two screen shots show data captured in table corresponding to the RAG query responses.
 
   Carefully compare the contents in table "pages" in the two screenshots below to the RAG application responses to queries in the above WEB UI screenshot, what do you see?.

   content scraped showing max driving speed of 120 km/hr on Expressway; RAG response cited the source as chunk 7 of "Driving in China" website.
   ```
   ![driving in china chunk 7](static/img/query-validation-in-postgres.png)

   ```
   content scraped showing max bullet train speed of 350 km/hr; RAG response cited the source as chunk 2 of "Rail travel in China" website.
   ```
   ![rail speed chunk2](static/img/query-validation2-inpostgres.png)

   These two screen shots are evidence that the responses from RAG application were indeed retrieved from our local knowledge base, and it was not part of the general answers from the LLM model itself.

## License

This project is licensed under the MIT License. 

## Resources

- [what is RAG](https://aws.amazon.com/what-is/retrieval-augmented-generation/)
- [open router](https://openrouter.ai/)
- [scrapy/spider settings](https://docs.scrapy.org/en/latest/topics/settings.html)
- [Fast API](https://fastapi.tiangolo.com/)
- [This Repository](https://github.com/nyang64/my-rag)
- [Documentation/README](https://github.com/nyang64/my-rag/README.md)
- [Issue](mailto://nyang63@gmail.com)  email nyang63@gmail.om
