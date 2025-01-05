# IBKR Short Cover Converter

The IBKR Short Cover Converter is a Python program designed to process and convert short and cover trades from IBKR XML data files into a format suitable for Portfolio Performance import. The program performs the following tasks:

1. Parses IBKR XML data files to extract trade information.
2. Aggregates trades based on order ID, symbol, type, order time, currency, and ISIN.
3. Converts short and cover trades into buy and sell orders by swapping the transaction fees and the net value of the positions.
4. Creates a CSV file with the converted orders to export into Portfolio Performance.
5. Filters out short and cover trades from the original XML files and saves the modified XML files.

# Usage

*Command Line Arguments*

- `-f`, `--files`: List of IBKR flex query XML files to process.
- `-o`, `--output`: Output CSV file for Portfolio Performance import (required).

*How to use*
- Ensure you have Python installed on your system.
- Install the required Python packages using pip:
    ```sh
    pip install pandas
    ```
- Perform IBKR flex query export 
- Run the program with the necessary arguments:
    ```
    python pp_short_selling_converter.py -f ibkr_export_1.xml  ibkr_export_2.xml -o pp_short_trade_import.csv
    ```
- Import the csv import configuration file ```csv-config.json``` into Portfolio Performance. 
- Import the generated CSV file into Portfolio Performance: ```File -> Import -> Templates -> IBKR Short Cover Import```  



