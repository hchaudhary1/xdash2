import streamlit as st

tab1, tab2 = st.tabs(["Simple-Screener", "Data-Explorer"])

with tab1:
    st.write("This is the Simple-Screener tab.")

with tab2:
    st.write("This is the Data-Explorer tab.")
