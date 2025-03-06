import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEndpoint
from src.db_connection import DatabaseIntegrations

class RAGchain:
    def __init__(self, user_question: str, chat_history: list):
        self.user_question = user_question
        self.chat_history = chat_history
        self.db_object = DatabaseIntegrations()
        self.repo_id = "mistralai/Mistral-7B-Instruct-v0.2"
        self.hf_api_key = st.secrets["LLM_API"]["HUGGING_FACE_API_KEY"]
        
    def db_schema(self):
        return self.db_object.get_schema()
    
    def execute_sql(self, query):
        try:
            return self.db_object.run_query(query)
        except Exception as db_error:
            return f"SQL execution error: {db_error}"
    
    def sql_subchain(self):
        sql_chain_template = """
            You are a data analyst at a music company. You are interacting with a user who is asking you questions about the company's database.
            Based on the table schema provided below, you need to generate SQL queries to answer the user's questions. Take the conversation history into account.
            
            <SCHEMA>{schema}</SCHEMA>
            
            Conersation History: {chat_history}
            
            Write only the SQL Query and nothing else. Do not wrap the SQL Query in any other text, not even backticks. Avoid linebreaks and output the SQL query in a single line without any comments or "\n".
            
            For Example:
            Question: Which 3 artists have the most tracks?
            SQL Query: SELECT ArtistId, COUNT(*) as track_count FROM Track GROUP BY ArtistId ORDER BY track_count DESC LIMIT 3;
            Question: Name 10 artists from the database.
            SQL Query: Select Name from Artist LIMIT 10;
            
            Your turn:
            
            Question: {question}
            SQL Query:
        """
        sql_chain_prompt = ChatPromptTemplate.from_template(template=sql_chain_template)
        llm = HuggingFaceEndpoint(repo_id=self.repo_id, temperature=0.1, huggingfacehub_api_token=self.hf_api_key)
        chain = (
            RunnablePassthrough.assign(schema=lambda _: self.db_schema)
            | sql_chain_prompt
            | llm
            | StrOutputParser()
        )
        sql_response = chain.invoke({"question": self.user_question, "chat_history": self.chat_history})
        return sql_response, chain
    
    def main_chain(self):
        try:
            sql_response, sql_chain = self.sql_subchain()
            main_chain_template = """
                You are a data analyst at a music company. You are interacting with a user who is asking you questions about the company's database.
                Based on the table schema provided below, user question, sql query, and sql query response, you need to generate a natural language response for the user.
                <SCHEMA>{schema}</SCHEMA>
                
                Conversation History: {chat_history}
                SQL Query: <SQL>{sql_query}</SQL>
                Question: {question}
                SQL Query Response: {response}
            """
            main_chain_prompt = ChatPromptTemplate.from_template(template=main_chain_template)
            llm = HuggingFaceEndpoint(repo_id=self.repo_id, temperature=0.1, huggingfacehub_api_token=self.hf_api_key)
            chain = (
                RunnablePassthrough.assign(sql_query=sql_chain).assign(
                    schema=lambda _ : self.db_schema,
                    response=lambda var: self.execute_sql(var["sql_query"]),
                )
                | main_chain_prompt
                | llm
                | StrOutputParser()
            )
            ai_response = chain.invoke({"question": self.user_question, "chat_history": self.chat_history, "sql_query": sql_response})
            return ai_response, sql_response
        except Exception as e:
            return f"An error occurred while running the SQL query. Error: {e}", sql_response