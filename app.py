import os
import streamlit as st
from sqlalchemy.engine.url import URL
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_huggingface import HuggingFaceEndpoint
from dotenv import load_dotenv
load_dotenv()

hf_api_key=st.secrets["LLM_API"]["HUGGING_FACE_API_KEY"]

db_uri=URL.create(
    "mysql+pymysql",
    username=st.secrets["DATABASE"]["DB_USER"],
    password=st.secrets["DATABASE"]["DB_PASSWORD"],
    host=st.secrets["DATABASE"]["DB_HOST"],
    port=st.secrets["DATABASE"]["DB_PORT"],
    database=st.secrets["DATABASE"]["DB_DATABASE"],
    query={
        "ssl_ca": st.secrets["DATABASE"]["CA"]
    }
)
db_connection=SQLDatabase.from_uri(db_uri)
cached_schema=db_connection.get_table_info()

def init_database(user: str, password: str, host: str, port: str, database: str):
    global cached_schema
    global db_connection
    db_uri=f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    db_connection=SQLDatabase.from_uri(db_uri)
    cached_schema=db_connection.get_table_info()

def get_schema(_):
    return cached_schema

def get_sql_chain():
    template=""""
        You are a data analyst at a music company. You are interacting with a user who is asking you questions about the company's database.
        Based on the table schema provided below, you need to generate SQL queries to answer the user's questions. Take the conversation history into account.
        
        <SCHEMA>{schema}</SCHEMA>
        
        Conersation History: {chat_history}
        
        Write only the SQL Query and nothing else. Do not wrap the SQL Query in any other text, not even backticks.
        
        For Example:
        Question: Which 3 artists have the most tracks?
        SQL Query: SELECT ArtistId, COUNT(*) as track_count FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;
        Question: Name 10 artists from the database.
        SQL Query: Select Name from Artist LIMIT 10;
        
        Your turn:
        
        Question: {question}
        SQL Query:
    """
    prompt=ChatPromptTemplate.from_template(template=template)
    repo_id="mistralai/Mistral-7B-Instruct-v0.2"
    llm=HuggingFaceEndpoint(repo_id=repo_id,temperature=0.1,huggingfacehub_api_token=hf_api_key)
    chain=(
        RunnablePassthrough.assign(schema=get_schema)
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain

def get_response(user_question: str, chat_history: list):
    try:
        sql_chain=get_sql_chain()
        template="""
            You are a data analyst at a music company. You are interacting with a user who is asking you questions about the company's database.
            Based on the table schema provided below, user question, sql query, and sql query response, you need to generate a natural language response for the user.
            <SCHEMA>{schema}</SCHEMA>
            
            Conversation History: {chat_history}
            SQL Query: <SQL>{sql_query}</SQL>
            Question: {question}
            SQL Query Response: {response}
        """
        prompt=ChatPromptTemplate.from_template(template=template)
        repo_id="mistralai/Mistral-7B-Instruct-v0.2"
        llm=HuggingFaceEndpoint(repo_id=repo_id,temperature=0.1,huggingfacehub_api_token=hf_api_key)
        def execute_sql(query):
            try:
                return db_connection.run(query)
            except Exception as db_error:
                return f"SQL execution error: {db_error}"
        chain=(
            RunnablePassthrough.assign(sql_query=sql_chain).assign(
                schema=lambda _: get_schema,
                response=lambda var: execute_sql(var["sql_query"]),
            )
            | prompt
            | llm
            | StrOutputParser()
        )
        return chain.invoke({"question": user_question, "chat_history": chat_history}),sql_chain.invoke({"question": user_question, "chat_history": chat_history})
    except Exception as e:
        return f"An error occurred while running the SQL query. Error: {e}",sql_chain.invoke({"question": user_question, "chat_history": chat_history})

# streamlit part 
if "chat_history" not in st.session_state:
    st.session_state.chat_history=[
        AIMessage("What can I query for you today?"),
    ]
    
if "db_settings" not in st.session_state:
    st.session_state.db_settings = {
        "user": os.getenv("DB_USER"),
        "password": os.getenv("DB_PASSWORD"),
        "host": os.getenv("DB_HOST"),
        "port": os.getenv("DB_PORT"),
        "database": os.getenv("DB_DATABASE"),
    }
if "sidebar_visible" not in st.session_state:
    st.session_state.sidebar_visible=False

st.set_page_config(page_title="SQL Query Generator", page_icon=":robot:")
st.title("🔍 QueryBot")
st.markdown(
    """
    **Hello, User! 🚀 I'm QueryBot - Your Smart SQL Query Generator AI Assistant! 🤖**\n
    _Built on the power of Mistral's 7B LLM model and Langchain framework_
    """
)
with st.sidebar:
    st.header("Database Settings")
    st.write("Configure your database settings here.")
    
    st.text_input("Host", value=st.session_state.db_settings["host"], key="db_host")
    st.text_input("User", value=st.session_state.db_settings["user"], key="db_user")
    st.text_input("Password", type="password", value=st.session_state.db_settings["password"], key="db_password")
    st.text_input("Port", value=st.session_state.db_settings["port"], key="db_port")
    st.text_input("Database", value=st.session_state.db_settings["database"], key="db_database")
    
    if st.button("🔌 Connect"):
        try:
            connect_db=init_database(
                user=st.session_state.db_user,
                password=st.session_state.db_password,
                host=st.session_state.db_host,
                port=st.session_state.db_port,
                database=st.session_state.db_database
            )
            st.session_state.db_connection=connect_db
            st.success("Connected to the database successfully!")
        except Exception as e:
            st.error(f"Failed to connect to the database. Error: {e}")
st.markdown("---")

for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI"):
            st.markdown(f"**QueryBot**: {message.content}")
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human"):
            st.markdown(f"👤 **You**: {message.content}")
user_question=st.chat_input("Enter your question here:")
if user_question is not None and user_question.strip()!="":
    st.session_state.chat_history.append(HumanMessage(content=user_question))
    with st.chat_message("Human"):
        st.markdown(f"👤 **You**: {user_question}")
    with st.chat_message("AI"):
        response,query=get_response(user_question, st.session_state.chat_history)
        st.markdown(response)
        st.markdown(
    '<div style="font-size:16px; color:#2E86C1; font-weight:bold;">🚀 Your Custom SQL Query:</div>', 
    unsafe_allow_html=True
)
        st.code(query)
    st.session_state.chat_history.append(AIMessage(content=response))