import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.title("Support Ticket AI Assistant")

tab1, tab2 = st.tabs(["Ask a Question", "View Anomalies"])

with tab1:
    st.subheader("Ask about the support tickets")
    question = st.text_input("Type your question here")

    if st.button("Ask"):
        if question.strip() == "":
            st.warning("Please type a question first")
        else:
            with st.spinner("Thinking..."):
                response = requests.post(f"{API_URL}/query", json={"question": question})

            if response.status_code == 200:
                result = response.json()
                st.write("**Answer:**", result["answer"])
                with st.expander("See generated SQL"):
                    st.code(result["sql"], language="sql")
            else:
                st.error("Something went wrong. Check if the API is running.")

with tab2:
    st.subheader("Flagged Anomalies")

    if st.button("Load Anomalies"):
        with st.spinner("Fetching..."):
            response = requests.get(f"{API_URL}/anomalies")

        if response.status_code == 200:
            data = response.json()
            st.write(f"Found **{data['count']}** anomalies")
            st.dataframe(data["anomalies"])
        else:
            st.error("Something went wrong. Check if the API is running.")