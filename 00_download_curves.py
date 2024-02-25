import datetime
import inspect
import json
import os
import requests
import time

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
    today = datetime.date.today().strftime("%Y-%m-%d")

    # Define the file and folder names based on the symphony_id and today's date
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


# tests
get_live_start_date("0bBsknsEveFj5INdknFS")
single_backtest("0bBsknsEveFj5INdknFS", "1990-01-01", "2024-02-18")
single_backtest("0bBsknsEveFj5INdknFS", "1990-01-01", "2024-02-18")
