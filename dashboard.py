import streamlit as st

def simple_screener_page():
    st.write("This is the Simple-Screener page.")
    # Add more code for Simple-Screener page here

def data_explorer_page():
    st.write("This is the Data-Explorer page.")
    # Add more code for Data-Explorer page here

PAGES = {
    "Simple-Screener": simple_screener_page,
    "Data-Explorer": data_explorer_page
}

selection = st.sidebar.radio("Navigation:", list(PAGES.keys()))
page_function = PAGES[selection]
page_function()

