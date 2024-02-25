import csv
import datetime
import inspect
import json
import os
import pandas as pd
import pytz
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


DATE_1990 = "1990-01-01"  # 11110
DATE_TODAY = datetime.date.today().strftime("%Y-%m-%d")
DATE_TWO_WEEKS_AGO = (datetime.date.today() - datetime.timedelta(weeks=2)).strftime(
    "%Y-%m-%d"
)
XOM_SYMPH_ID = "cv9jhez5EhhG00KHDlly"
DELISTED_SYMPH_ID = "Do36TWTu1gWh8SewO1Go"
last_call_time = None


def v_print(*args, **kwargs):
    global last_call_time

    # Get the current time
    now = datetime.datetime.now()

    # Calculate the time in ms since the last call, if there was a previous call
    if last_call_time is not None:
        time_since_last_call = (now - last_call_time).total_seconds() * 1000
        # Round the time to three decimal places
        time_since_last_call = f"+{time_since_last_call:.3f} ms"
    else:
        time_since_last_call = "+0.000 ms"

    # Update the last call time to now for the next call
    last_call_time = now

    # Get the previous frame in the stack, which is the caller of this function
    caller_frame = inspect.stack()[1]
    # Extract the function name and line number from the caller frame
    function_name = caller_frame.function
    line_number = caller_frame.lineno

    # Prepare the prefix with the new order and formatting
    prefix = f"[{now.strftime('%H:%M:%S')}] [{time_since_last_call}] [{function_name}:{line_number}]"

    # Print the prefix along with the original message
    print(prefix, *args, **kwargs)


def epoch_days_to_date(days: int) -> datetime.date:
    return datetime.datetime.fromtimestamp(days * 24 * 60 * 60, tz=pytz.UTC).date()


def single_backtest(symph_id, start_date, end_date, max_retries=3):
    v_print("start")
    file_name = f"2_{symph_id}-{start_date}-to-{end_date}.json"
    folder_name = "backtest_results"

    # Ensure the folder exists
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Construct the full file path
    file_path = os.path.join(folder_name, file_name)

    try:
        # Check if the results file already exists
        if os.path.exists(file_path):
            v_print(f"Reading from existing file {file_name}")
            with open(file_path, "r") as file:
                return json.load(file)
    except Exception as e:
        v_print(f"An error occurred while reading from cache: {e}")

    data = (
        '["^ ","~:benchmark_symphonies",[],"~:benchmark_tickers",[],"~:backtest_version","v2","~:apply_reg_fee",true,"~:apply_taf_fee",true,"~:slippage_percent",0.0005,"~:start_date","'
        + str(start_date)
        + '","~:capital",10000,"~:end_date","'
        + str(end_date)
        + '"]'
    )
    url = (
        "https://backtest-api.composer.trade/api/v2/public/symphonies/"
        + symph_id
        + "/backtest"
    )
    headers = {
        "content-type": "application/transit+json",
    }
    retries = 0
    while retries < max_retries:
        retries += 1
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            # Cache the result to disk
            with open(file_path, "w") as file:
                json.dump(response.json(), file)
                v_print(f"Result saved to disk {file_name}")
            return response.json()
        except requests.exceptions.RequestException as e:
            v_print(f"Error executing backtest for id {symph_id}: {e}")
            if retries < max_retries:
                v_print(f"Retrying... Attempt {retries}/{max_retries}")
                time.sleep(1)  # Add a small delay before retrying
            else:
                v_print(f"Maximum retries ({max_retries}) reached. Aborting.")
                return None
        except Exception as e:
            v_print(
                f"An unexpected error occurred during backtest for id {symph_id}: {e}"
            )
            return None


def get_live_start_date(symphony_id, max_retries=3, retry_delay=2):
    # Get today's date in YYYY-MM-DD format
    # Define the file and folder names based on the symphony_id and today's date
    file_name = f"{symphony_id}-live_start_date-{DATE_TODAY}.json"
    folder_name = "live_start_dates"

    # Ensure the folder exists
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Construct the full file path
    file_path = os.path.join(folder_name, file_name)

    # Check if the results file already exists
    if os.path.exists(file_path):
        v_print(f"Reading from existing file {file_name}")
        with open(file_path, "r") as file:
            data = json.load(file)
            # Check if 'last_semantic_update_at' key exists
            if "fields" in data and "last_semantic_update_at" in data["fields"]:
                return data["fields"]["last_semantic_update_at"][
                    "timestampValue"
                ].split("T")[0]
            else:
                v_print(
                    f"'last_semantic_update_at' key not found in the file {file_name}."
                )
                return None

    retries = 0
    while retries < max_retries:
        retries += 1
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
                v_print(
                    f"Access denied with 403 Forbidden error for symphony {symphony_id}."
                )
                return None  # Return immediately if 403 error encountered
            response.raise_for_status()
            data = response.json()

            # Save the response to disk
            with open(file_path, "w") as file:
                json.dump(data, file)
                v_print(f"Saved response to {file_path}")

            if "fields" in data and "last_semantic_update_at" in data["fields"]:
                return data["fields"]["last_semantic_update_at"][
                    "timestampValue"
                ].split("T")[0]
            else:
                v_print(f"'last_semantic_update_at' key not found in the response.")
                return None

        except requests.exceptions.RequestException as e:
            v_print(f"Error getting live start date for symphony {symphony_id}: {e}")
            if retries < max_retries:
                v_print("Retrying...")
                time.sleep(retry_delay)
        except Exception as e:
            v_print(
                f"An unexpected error occurred in get_live_start_date for symphony {symphony_id}: {e}"
            )
            return None

    v_print(f"Maximum retries exceeded for symphony {symphony_id}")
    return None


def get_symphony_list(file_path):
    """Reads the first column from a CSV file and returns a list of IDs, skipping the header."""
    with open(file_path, newline="") as csvfile:
        reader = csv.reader(csvfile)
        next(reader)  # Skip the header row
        return [row[0] for row in reader if row]  # Added check to skip empty rows


def download_multiple_backtests(symphony_ids, start_date, end_date):
    """
    Downloads backtest data using a ThreadPoolExecutor.
    """
    with ThreadPoolExecutor() as executor:
        # Create a future to symphony_id mapping by submitting tasks directly using single_backtest
        future_to_symph_id = {
            executor.submit(single_backtest, symph_id, start_date, end_date): symph_id
            for symph_id in symphony_ids
        }

        for future in as_completed(future_to_symph_id):
            symph_id = future_to_symph_id[future]
            try:
                result = (
                    future.result()
                )  # No need to unpack a tuple, as we're directly getting the result
                v_print(f"Completed backtest for {symph_id}")
            except Exception as exc:
                v_print(f"{symph_id} generated an exception: {exc}")


def get_size_of_symphony(symphony_id):
    v_print(f"get size: {symphony_id}")
    today = DATE_TODAY

    file_name = f"{symphony_id}-score-{today}.json"
    folder_name = "symphony_scores"

    # Ensure the folder exists
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Construct the full file path
    file_path = os.path.join(folder_name, file_name)

    # Check if the file already exists
    if os.path.exists(file_path):
        v_print(f"Reading from existing file {file_name}")
        with open(file_path, "r") as file:
            data = file.read()
            return len(data)

    try:
        url = (
            "https://backtest-api.composer.trade/api/v1/public/symphonies/"
            + symphony_id
            + "/score?score_version=v2"
        )

        response = requests.get(url)
        response.raise_for_status()
        data = response.text

        # Save the response to disk
        with open(file_path, "w") as file:
            file.write(data)
            v_print(f"Saved response to {file_path}")

        return len(data)
    except requests.exceptions.RequestException as e:
        v_print(f"Error getting size of symphony {symphony_id}: {e}")
        return None
    except Exception as e:
        v_print(
            f"An unexpected error occurred in get_size_of_symphony for symphony {symphony_id}: {e}"
        )
        return None


def latest_market_day_int():
    if not hasattr(latest_market_day_int, "last_market_day"):
        curve = single_backtest(XOM_SYMPH_ID, DATE_TWO_WEEKS_AGO, DATE_TODAY)
        curve = dict(sorted(curve["dvm_capital"][XOM_SYMPH_ID].items()))
        latest_market_day_int.last_market_day = list(curve.keys())[-1]
    return latest_market_day_int.last_market_day


def find_min_date_int(sym_id):
    full_curve = single_backtest(sym_id, DATE_1990, DATE_TODAY)
    curve = dict(sorted(full_curve["dvm_capital"][sym_id].items()))
    min_date = list(curve.keys())[0]
    max_date = list(curve.keys())[-1]
    if latest_market_day_int() == max_date:
        return int(min_date)
    else:
        # since max date is not valid -- we wont use this symph
        v_print(f"Max Date: {max_date}, Latest Market Day: {latest_market_day_int()}")
        return None


def get_symph_dates():
    symphony_ids = get_symphony_list("2024-01-28.csv")
    df = pd.DataFrame(symphony_ids, columns=["id"])
    df = df.head(100)

    df["info_size"] = None
    df["info_start_date"] = None
    df["info_live_date"] = None

    def process_row(row):
        symphony_id = row.id
        live_start_date = get_live_start_date(symphony_id)
        if live_start_date is None:
            return None

        min_date = find_min_date_int(symphony_id)
        if min_date is None:
            return None

        row_dict = row._asdict()
        row_dict["info_live_date"] = live_start_date
        row_dict["info_start_date"] = epoch_days_to_date(min_date)
        row_dict["info_size"] = get_size_of_symphony(symphony_id)
        return row_dict

    with ThreadPoolExecutor() as executor:
        for index, row in enumerate(
            executor.map(process_row, df.itertuples(index=False))
        ):
            if row is not None:
                df.at[index, "info_size"] = row["info_size"]
                df.at[index, "info_start_date"] = row["info_start_date"]
                df.at[index, "info_live_date"] = row["info_live_date"]

    df = df.dropna(subset=["info_live_date"])
    df = df.dropna(subset=["info_start_date"])
    df.to_csv("output.csv", index=False)
    return df


def main():
    df = get_symph_dates()

    v_print("--- DONE ---")


if __name__ == "__main__":
    main()
