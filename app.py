import os
import streamlit as st
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import GoogleGenerativeAI
from dotenv import load_dotenv
load_dotenv()

def init_database(user: str, password: str, host: str, port: str, database: str):
    db=f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    return SQLDatabase.from_uri(db)

def get_sql_chain(db):
    connected_db=init_database(**db)
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
    llm=GoogleGenerativeAI(model="gemini-pro",api_key=os.getenv("API_KEY"))

    def get_schema(_):
        return connected_db.get_table_info()
    
    chain=(
        RunnablePassthrough.assign(schema=get_schema)
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain


# streamlit part 
if "chat_history" not in st.session_state:
    st.session_state.chat_history=[
        AIMessage("Hello! I am a SQL Query Generator bot. How can I help you today?"),
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
st.title("🔍 SQL Query Generator")
st.markdown(
    """
    **Welcome to the SQL Query Generator!**  
    Easily convert your questions about your database into executable SQL queries.
    _Powered by Google-Gemini-AI and LangChain._
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
        sql_chain=get_sql_chain(st.session_state.db_settings)
        response=sql_chain.invoke({
            "chat_history": st.session_state.chat_history,
            "question": user_question
        })
        st.markdown(response)
    st.session_state.chat_history.append(AIMessage(content=response))





# def wrap_text(text, width=35):
#     return '\n'.join(textwrap.wrap(text, width))

# if st.button("💡 Generate SQL Query"):
#     if question:
#         with st.spinner("Generating SQL Query... Please wait!"):
#             sql_query, db_response = chain(question)  # Assuming chain() function exists for query generation
#             if sql_query:
#                 st.success("✅ SQL Query Generated!")
#                 wrapped_sql_query = wrap_text(sql_query, width=35)
#                 col1, col2 = st.columns([1, 1])
#                 # Left column: SQL query
#                 with col1:
#                     st.markdown("### 🧾 Generated SQL Query")
#                     st.code(wrapped_sql_query, language="sql")
#                 # Right column: Database response
#                 with col2:
#                     if db_response is not None:
#                         st.markdown("### 📊 Database Response")
#                         st.markdown(db_response)
#                     else:
#                         st.markdown("### 📊 Database Response")
#                         st.error("⚠️ No result obtained from the database. Please re-check your query.")
#             else:
#                 st.error("⚠️ Failed to generate SQL query. Please re-check your question.")
#     else:
#         st.warning("⚠️ Please enter a question to generate the SQL query.")

# # Footer with Help and GitHub Link
# st.markdown("---")
# st.markdown(
#     """
#     **Need Help?**  
#     For any issues, feel free to raise an issue at [Github](https://github.com/Gaurav-576/QueryBot).
#     _Happy Querying!_
#     """
# )

# # Custom CSS for better UI (Optional)
# st.markdown(
#     """
#     <style>
#         body {
#             font-family: 'Roboto', sans-serif;
#             background-color: #f4f7fa;
#             color: #333;
#         }

#         h1 {
#             color: #4a90e2;
#             text-align: center;
#             font-size: 2.5rem;
#         }

#         h3 {
#             color: #6c757d;
#             font-size: 1.5rem;
#         }

#         .description {
#             background-color: #f1f3f5;
#             padding: 20px;
#             border-radius: 8px;
#             margin-bottom: 30px;
#         }

#         .stTextInput input {
#             background-color: #ffffff;
#             color: #333;  /* Set text color to black */
#             padding: 12px;
#             border-radius: 8px;
#             border: 1px solid #ddd;
#             font-size: 1rem;
#         }

#         .stButton>button {
#             background-color: #4a90e2;
#             color: white;
#             font-weight: bold;
#             border-radius: 5px;
#             padding: 10px 15px;
#             cursor: pointer;
#         }

#         .stButton>button:hover {
#             background-color: #357ab8;
#         }

#         .stTextInput>div>label {
#             font-size: 1rem;
#             color: #6c757d;
#         }

#         .stCode block {
#             background-color: #f8f9fa;
#             padding: 15px;
#             border-radius: 8px;
#             font-size: 1rem;
#             color: #343a40;
#         }

#         .stTextInput input:focus {
#             outline: 2px solid #4a90e2;
#         }

#         .stAlert {
#             margin-bottom: 15px;
#         }

#         .footer {
#             font-size: 1rem;
#             text-align: center;
#             margin-top: 40px;
#             color: #6c757d;
#         }
#     </style>
#     """,
#     unsafe_allow_html=True
# )
