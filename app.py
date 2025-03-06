import streamlit as st
from src.db_connection import DatabaseIntegrations
from src.rag_chains import RAGchain
from langchain_core.messages import AIMessage, HumanMessage

db_object = DatabaseIntegrations()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        AIMessage("What can I query for you today?"),
    ]
    
if "db_settings" not in st.session_state:
    st.session_state.db_settings = {
        "user": st.secrets["DATABASE"]["DB_USER"],
        "password": "",
        "host": st.secrets["DATABASE"]["DB_HOST"],
        "port": st.secrets["DATABASE"]["DB_PORT"],
        "database": st.secrets["DATABASE"]["DB_DATABASE"],
    }
if "sidebar_visible" not in st.session_state:
    st.session_state.sidebar_visible = False

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
            connect_db=db_object.set_database(
                user=st.session_state.db_user,
                password=st.session_state.db_password,
                host=st.session_state.db_host,
                port=st.session_state.db_port,
                database=st.session_state.db_database
            )
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
            
user_question = st.chat_input("Enter your question here:")
if user_question is not None and user_question.strip() != "":
    st.session_state.chat_history.append(HumanMessage(content=user_question))
    with st.chat_message("Human"):
        st.markdown(f"👤 **You**: {user_question}")
    with st.chat_message("AI"):
        RAG_object = RAGchain(user_question=user_question, chat_history=st.session_state.chat_history)
        response, query = RAG_object.main_chain()
        st.markdown(response)
        st.markdown(
    '<div style="font-size:16px; color:#2E86C1; font-weight:bold;">🚀 Your Custom SQL Query:</div>', 
    unsafe_allow_html=True
)
        st.code(query)
    st.session_state.chat_history.append(AIMessage(content=response))