import streamlit as st
from simple_screener import simple_screener_page


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

