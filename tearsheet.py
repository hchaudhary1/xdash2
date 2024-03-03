import datetime
import os
import pandas as pd
import quantstats as qs
import requests
import streamlit as st
import time
from download_curves import single_backtest, epoch_days_to_date
from pyhtml2pdf import converter

ONLY_LIVE = "Only LIVE data"
ALL_DATA = "All data (before and after LIVE)"

def single_tearsheet():
    option1 = st.selectbox("Select Time Range:", (ONLY_LIVE, ALL_DATA))

    def get_live_start_date(symphony_id, max_retries=3, retry_delay=2):
        retries = 0
        while retries < max_retries:
            try:
                url = (
                    "https://firestore.googleapis.com/v1/projects/leverheads-278521/databases/(default)/documents/symphony/"
                    + symphony_id
                )

                headers = {
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }

                response = requests.get(url, headers=headers)
                if response.status_code == 403:  # Check for 403 Forbidden status code
                    print(
                        f"Access denied with 403 Forbidden error for symphony {symphony_id}."
                    )
                    return None  # Return immediately if 403 error encountered

                response.raise_for_status()  # This will raise an exception for HTTP errors other than 403
                data = response.json()
                return data["fields"]["last_semantic_update_at"][
                    "timestampValue"
                ].split("T")[0]

            except requests.exceptions.RequestException as e:
                print(f"Error getting live start date for symphony {symphony_id}: {e}")
                retries += 1
                if retries < max_retries:
                    print("Retrying...")
                    time.sleep(retry_delay)
            except Exception as e:
                print(
                    f"An unexpected error occurred in get_live_start_date for symphony {symphony_id}: {e}"
                )
                return None

        print(f"Maximum retries exceeded for symphony {symphony_id}")
        return None

    def calculate_returns_from_dvm_capital(dvm_capital):
        try:
            dvm_capital = dict(sorted(dvm_capital.items()))
            dvm_capital = {
                epoch_days_to_date(int(k)): v for k, v in dvm_capital.items()
            }
            returns = pd.Series(dvm_capital).pct_change().dropna()

            # Convert the index to DatetimeIndex if it's not already
            returns.index = pd.to_datetime(returns.index)

            return returns
        except Exception as e:
            print(
                f"An unexpected error occurred in calculate_returns_from_dvm_capital: {e}"
            )
            return None

    def read_html_file(file_path):
        with open(file_path, "r") as file:
            html_content = file.read()
        return html_content

    async def generate_pdf_from_html(html_content, file_path):
        browser = await launch()
        page = await browser.newPage()

        await page.setContent(html_content)

        await page.pdf({"path": file_path, "format": "A4"})

        await browser.close()

    # make a input box for symphony id
    symphony_id = st.text_input("Enter Symphony ID", value="")
    # create a button to submit the symphony id
    symphony_id_button = st.button("Submit")
    # if the button is clicked, then do the following

    if symphony_id_button:
        # if the symphony id is not empty
        if symphony_id != "":
            if option1 == ONLY_LIVE:
                # get the live start date
                live_start_date = get_live_start_date(symphony_id)

                # if the live start date is not None
                if live_start_date is not None:
                    # print the live start date
                    st.write(f"Live Start Date: {live_start_date}")

                    # get the symphony data
                    backtest = single_backtest(
                        symphony_id,
                        live_start_date,
                        datetime.date.today().strftime("%Y-%m-%d")
                    )
                    returns = calculate_returns_from_dvm_capital(
                        backtest["dvm_capital"][symphony_id]
                    )
                    qs.reports.html(
                        returns,
                        output=str(symphony_id) + "_tearsheet.html",
                        title=str(symphony_id) + " Tearsheet",
                    )
                    # convert it to pdf
                    st.write("TearSheet computed. Generating PDF....")

                    # read the html file
                    html_content = read_html_file(str(symphony_id) + "_tearsheet.html")
                    # convert the html to pdf
                    if html_content is not None:
                        import os
                        from pyhtml2pdf import converter

                        path = os.path.abspath(str(symphony_id) + "_tearsheet.html")
                        converter.convert(
                            f"file://{path}", str(symphony_id) + "_tearsheet.pdf"
                        )

                        # Now, read the generated PDF file
                        with open(
                            str(symphony_id) + "_tearsheet.pdf", "rb"
                        ) as pdf_file:
                            pdf_data = pdf_file.read()

                        # Download the PDF file
                        st.download_button(
                            label="Download PDF",
                            data=pdf_data,
                            file_name=str(symphony_id) + "_tearsheet.pdf",
                            mime="application/pdf",
                        )

            elif option1 == ALL_DATA:
                # set date 1/1/1990 as the start date
                start_date = datetime.datetime(1990, 1, 1).strftime("%Y-%m-%d")
                # get the symphony data
                backtest = single_backtest(
                    symphony_id,
                    start_date,
                    datetime.date.today()
                )
                returns = calculate_returns_from_dvm_capital(
                    backtest["dvm_capital"][symphony_id]
                )
                qs.reports.html(
                    returns,
                    output=str(symphony_id) + "_tearsheet.html",
                    title=str(symphony_id) + " Tearsheet",
                )
                # convert it to pdf
                st.write("TearSheet computed. Generating PDF....")

                # read the html file
                html_content = read_html_file(str(symphony_id) + "_tearsheet.html")
                # convert the html to pdf
                if html_content is not None:
                    import os
                    from pyhtml2pdf import converter

                    path = os.path.abspath(str(symphony_id) + "_tearsheet.html")
                    converter.convert(
                        f"file://{path}", str(symphony_id) + "_tearsheet.pdf"
                    )

                    # Now, read the generated PDF file
                    with open(str(symphony_id) + "_tearsheet.pdf", "rb") as pdf_file:
                        pdf_data = pdf_file.read()

                    # Download the PDF file
                    st.download_button(
                        label="Download PDF",
                        data=pdf_data,
                        file_name=str(symphony_id) + "_tearsheet.pdf",
                        mime="application/pdf",
                    )

            else:
                # print that the live start date is not available
                st.write("Live Start Date not available")
        else:
            # print that the symphony id is empty
            st.write("Symphony ID is empty")
