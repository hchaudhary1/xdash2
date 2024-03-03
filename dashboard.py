import streamlit as st
from simple_screener import simple_screener_page

# Hide the Streamlit settings menu
hide_settings_menu = """
    <style>
        #MainMenu {visibility: hidden;}
    </style>
    """
st.markdown(hide_settings_menu, unsafe_allow_html=True)


def data_explorer_page():
    st.write("This is the Advacned Explorer page.")
    # Add more code for Data-Explorer page here

PAGES = {
    "Simple Selector": simple_screener_page,
    "Advacned Explorer": data_explorer_page
}

selection = st.sidebar.radio("Navigation:", list(PAGES.keys()))
page_function = PAGES[selection]
page_function()

