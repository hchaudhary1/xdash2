no import streamlit as st

PAGES = {
    "Simple-Screener": "This is the Simple-Screener page.",
    "Data-Explorer": "This is the Data-Explorer page."
}

selection = st.sidebar.radio("Go to", list(PAGES.keys()))
page = PAGES[selection]
st.write(page)

