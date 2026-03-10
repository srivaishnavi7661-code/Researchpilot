import streamlit as st
# Import your existing logic here (not Flask routes)
from researchpilot import search_papers, summarize_paper, chat_message, get_insights

st.title("🔬 ResearchPilot")

# Sidebar for navigation
page = st.sidebar.selectbox("Choose a feature", ["Search Papers", "Summarize Paper", "Chat Assistant", "Research Insights"])

if page == "Search Papers":
    st.header("Search Research Papers")
    query = st.text_input("Enter a research topic")
    max_results = st.slider("Max results", 5, 20, 10)
    if st.button("Search"):
        if query:
            result = search_papers(query, max_results)
            if 'error' in result:
                st.error(result['error'])
            else:
                st.success(f"Found {result['total']} papers")
                for paper in result['papers']:
                    with st.expander(paper['title']):
                        st.write(f"**Authors:** {', '.join(paper['authors'])}")
                        st.write(f"**Published:** {paper['published']}")
                        st.write(f"**Abstract:** {paper['abstract']}")
                        st.markdown(f"[Read Paper]({paper['url']})")
        else:
            st.warning("Please enter a query")

elif page == "Summarize Paper":
    st.header("Summarize a Paper")
    title = st.text_input("Paper Title")
    abstract = st.text_area("Paper Abstract")
    summary_type = st.selectbox("Summary Type", ["concise", "detailed", "eli5"])
    if st.button("Summarize"):
        if abstract:
            result = summarize_paper(title, abstract, summary_type)
            if 'error' in result:
                st.error(result['error'])
            else:
                st.write(result['summary'])
        else:
            st.warning("Please enter the abstract")

elif page == "Chat Assistant":
    st.header("AI Research Chat Assistant")
    message = st.text_input("Ask a question")
    context = st.text_area("Optional paper context")
    if st.button("Send"):
        if message:
            result = chat_message(message, context=context)
            if 'error' in result:
                st.error(result['error'])
            else:
                st.write(result['reply'])
        else:
            st.warning("Please enter a message")

elif page == "Research Insights":
    st.header("Research Insights & Trends")
    topic = st.text_input("Enter a research topic for analysis")
    if st.button("Get Insights"):
        if topic:
            result = get_insights(topic=topic)
            if 'error' in result:
                st.error(result['error'])
            else:
                st.write(result['insights'])
        else:
            st.warning("Please enter a topic")
