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
DATE_TODAY = datetime.date.today()
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
    if isinstance(start_date, str):
        start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    if isinstance(end_date, str):
        end_date = datetime.datetime.strptime(end_date, "%Y-%m-%d")

    start_date = start_date.strftime("%Y-%m-%d")
    end_date = end_date.strftime("%Y-%m-%d")

    v_print(f"backtest: {symph_id}: {start_date}-to-{end_date}")
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
    today = DATE_TODAY.strftime("%Y-%m-%d")
    file_name = f"{symphony_id}-live_start_date-{today}.json"
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
        return [row[1] for row in reader if row]  # Added check to skip empty rows


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
    today = DATE_TODAY.strftime("%Y-%m-%d")

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
        curve = single_backtest(
            XOM_SYMPH_ID, DATE_TWO_WEEKS_AGO, DATE_TODAY.strftime("%Y-%m-%d")
        )
        curve = dict(sorted(curve["dvm_capital"][XOM_SYMPH_ID].items()))
        latest_market_day_int.last_market_day = list(curve.keys())[-1]
    return latest_market_day_int.last_market_day


def find_min_date_int(sym_id):
    full_curve = single_backtest(sym_id, DATE_1990, DATE_TODAY.strftime("%Y-%m-%d"))
    curve = dict(sorted(full_curve["dvm_capital"][sym_id].items()))
    min_date = list(curve.keys())[0]
    max_date = list(curve.keys())[-1]
    if latest_market_day_int() == max_date:
        return int(min_date) + 1
    else:
        # since max date is not valid -- we wont use this symph
        v_print(f"Max Date: {max_date}, Latest Market Day: {latest_market_day_int()}")
        return None


def get_symph_dates():
    symphony_ids = get_symphony_list("2024-feb-25.csv")
    df = pd.DataFrame(symphony_ids, columns=["id"])

    df.loc[:, "info_size"] = None
    df.loc[:, "info_start_date"] = None
    df.loc[:, "info_live_date"] = None

    df = df.head(100)

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
    return df


def get_era_dates(isAfterLive, data_begin, live_date, delta_days, isBeyondDelta=False):
    bt_start = None
    bt_end = None
    if isAfterLive:
        era_date_mark = live_date + datetime.timedelta(days=delta_days)
        # assumes algos are pre-filtered and running live today
        if era_date_mark <= DATE_TODAY:
            # max AFTER is valid
            bt_start = live_date
            bt_end = era_date_mark
            if isBeyondDelta:
                bt_end = DATE_TODAY
    else:
        era_date_mark = live_date - datetime.timedelta(days=delta_days)
        if era_date_mark >= data_begin:
            # max BEFORE is valid
            bt_start = era_date_mark
            bt_end = live_date
            if isBeyondDelta:
                bt_start = data_begin

    return bt_start, bt_end


def process_row(row, isAfter=False):

    # names
    era_prefix = "BeforeLive"
    if isAfter:
        era_prefix = "AfterLive"

    era = [
        (30, "01mo"),
        (90, "03mo"),
        (180, "06mo"),
        (365, "12mo"),
    ]
    period_final = "13moToMax"
    delta_days_13mo = 395

    stat_types = {
        "GainTotalPct": ("cumulative_return", 0, 100),
        "GainAnnualizedPct": ("annualized_rate_of_return", 0, 100),
        "DrawdownMaxPct": ("max_drawdown", 0, 100),
        "Calmar": ("calmar_ratio", 100000, 1),
        "Sharpe": ("sharpe_ratio", 100, 1),
        "DayBestPct": ("max", 0, 100),
        "DayWorstPct": ("min", 0, 100),
        "DayAvgPct": ("mean", 0, 100),
        "DayStdDevPct": ("standard_deviation", 0, 6.2994078834871),
    }

    results = {}
    results[row["id"]] = row["id"]

    # dates
    live_date = pd.to_datetime(row["info_live_date"]).date()
    start_date = pd.to_datetime(row["info_start_date"]).date()
    bt_start = None
    bt_end = None

    # Iterate through each stat type and get stats
    for stat_name, stat_tuple in stat_types.items():
        stat_json_name, default_value, multiplier = stat_tuple

        # get stat for period_final first, as this is a max
        results_key = f"{stat_name}_{era_prefix}_{period_final}"
        results[results_key] = None
        bt_start, bt_end = get_era_dates(
            isAfter, start_date, live_date, delta_days_13mo, True
        )
        if bt_start is not None and bt_end is not None:
            json = single_backtest(row["id"], bt_start, bt_end)
            results[results_key] = (
                json["stats"].get(stat_json_name, default_value) * multiplier
            )

        # get stats for rest of the eras
        for days, description in era:
            results_key = f"{stat_name}_{era_prefix}_{description}"
            results[results_key] = None
            bt_start, bt_end = get_era_dates(isAfter, start_date, live_date, days)
            if bt_start is not None and bt_end is not None:
                json = single_backtest(row["id"], bt_start, bt_end)
                results[results_key] = (
                    json["stats"].get(stat_json_name, default_value) * multiplier
                )

    return results


def before_live(df):
    with ThreadPoolExecutor() as executor:
        all_results = []
        for is_after in [False, True]:
            all_results.extend(
                executor.map(
                    lambda row: process_row(row, is_after), df.to_dict("records")
                )
            )
        results = list(all_results)

    for curr_row_dict in results:
        if curr_row_dict is None:
            continue
        symph_id_key = list(curr_row_dict.keys())[0]
        symph_id = curr_row_dict.pop(symph_id_key)

        # copy data for symph_id into df
        for column_key, value in curr_row_dict.items():
            matching_rows = df.index[df["id"] == symph_id].tolist()
            if matching_rows:
                row_index = matching_rows[0]
                df.at[row_index, column_key] = value


def main():
    df = get_symph_dates()
    before_live(df)

    first_columns = ["id", "info_size", "info_start_date", "info_live_date"]
    remaining_columns = sorted([col for col in df.columns if col not in first_columns])
    new_order = first_columns + remaining_columns
    df = df[new_order]

    df.to_csv("output.csv", index=False)
    print(df.tail(10))


# before live
# after live
# before today

# more than 12

if __name__ == "__main__":
    main()
