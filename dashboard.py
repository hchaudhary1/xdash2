import pandas as pd
import pygwalker as pyg
import streamlit as st
import streamlit.components.v1 as components
from simple_screener import simple_screener_page
from tearsheet import single_tearsheet

st.set_page_config(layout="wide")

# Hide the Streamlit settings menu
hide_settings_menu = """
    <style>
        #MainMenu {visibility: hidden;}
    </style>
    """
st.markdown(hide_settings_menu, unsafe_allow_html=True)



def data_explorer_page():
    st.write("Advacned Explorer page. It may take a second to load...")
    df = pd.read_csv(
        "./output.csv",
        na_values=[
            "#N/A N/A",
            "#N/A",
            "N/A",
            "n/a",
            "nan",
            "NaN",
            "NA",
            "nan",
            "NAN",
            "",
        ],
    )
    
    pyg_html = pyg.to_html(df, env='Streamlit', spec=vis_spec)
    components.html(pyg_html, height=1000, scrolling=False)

PAGES = {
    "Simple Selector": simple_screener_page,
    "Advacned Explorer": data_explorer_page,
    "Single ID QuantStat": single_tearsheet
}

selection = st.sidebar.radio("Navigation:", list(PAGES.keys()))
page_function = PAGES[selection]
page_function()

