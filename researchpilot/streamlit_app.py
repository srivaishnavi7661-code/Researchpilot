import streamlit as st
# Import your existing logic here (not Flask routes)
# e.g. from researchpilot.app import summarize, search_papers

st.title("🔬 ResearchPilot")
query = st.text_input("Enter a research topic")
if st.button("Search"):
    # call your search/summarize functions here
    st.write("Results will appear here...")