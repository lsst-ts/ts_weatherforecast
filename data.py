import json
from prettytable import PrettyTable, PLAIN_COLUMNS

def main():
    with open("forecast.json") as f:
        df = json.load(f)
    table = PrettyTable()
    for key, value in df["trend_1h"].items():
        table.add_column(key, value)
    table.align = "l"
    table.set_style(PLAIN_COLUMNS)
    print(table.get_string(start=0, end=10, fields=["time", "temperature"]))

if __name__ == "__main__":
    main()
