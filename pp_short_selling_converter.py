#!/bin/python
import xml.etree.ElementTree as ET
from datetime import datetime
import pandas as pd
import argparse


def determine_trade_type(buy_Sell, open_close_indicator):
    trade_types = {
        ("BUY", "O"): "BUY",
        ("BUY", "C"): "COVER",
        ("SELL", "O"): "SHORT",
        ("SELL", "C"): "SELL"
    }
    return trade_types.get((buy_Sell, open_close_indicator), "Unknown Type")


def parse_ib_data_xml(file_path):
    dt_string = '%Y%m%d;%H%M%S'
    trades = []
    tree = ET.parse(file_path)
    for elem in tree.getroot().findall(".//Trades/Trade"):
        trade_type = determine_trade_type(elem.attrib["buySell"],
                                          elem.attrib["openCloseIndicator"])
        trades.append({
            "symbol": elem.attrib["symbol"],
            "order_id": elem.attrib["ibOrderID"],
            "order_time": datetime.strptime(elem.attrib["orderTime"], dt_string),
            "type": trade_type,
            "quantity": elem.attrib["quantity"],
            "netCash": elem.attrib["netCash"],
            "commission": elem.attrib["ibCommission"],
            "tradeMoney": elem.attrib["tradeMoney"],
            'currency': elem.attrib['currency'],
            'isin': elem.attrib['isin'],
            "exec_time": datetime.strptime(elem.attrib["dateTime"], dt_string),
            'trade_id': elem.attrib['tradeID'],
            'transaction_id': elem.attrib['transactionID']
        })
    return trades


def init_pd_display():
    pd.set_option('display.max_columns', None)  # or 1000
    pd.set_option('display.max_rows', None)  # or 1000
    pd.set_option('display.max_colwidth', None)  # or 199
    pd.set_option('display.width', None)  # or 199


def aggregate_trades(df_trades):
    agg_df = df_trades.groupby(
        ['order_id', 'symbol', 'type', 'order_time', 'currency', 'isin']
    ).agg(
        {
            'quantity': 'sum',
            'netCash': 'sum',
            'commission': 'sum',
            'tradeMoney': 'sum',
            'exec_time': 'max',
            'trade_id': 'first',
            'transaction_id': 'first'
        }
    ).reset_index()
    agg_df = agg_df.sort_values(by='exec_time')
    return agg_df


# Assuming agg_df is already defined
def convert_short_cover2buy_sell_orders(df):
    short_df = df[df['type'] == 'SHORT']
    cover_df = df[df['type'] == 'COVER']
    buy_sell_orders = []

    for _, short_entry in short_df.iterrows():
        # Find the corresponding COVER entry with the same quantity
        # Only the full covered close (quantity) of the position is evaluated
        cover = cover_df[
            (cover_df['quantity'] == short_entry['quantity'] * -1)
            & (cover_df['symbol'] == short_entry['symbol'])
            & (cover_df['exec_time'] > short_entry['exec_time'])
            ]

        if cover.empty:
            print(f"Short not covered: {short_entry}")
            continue
        cover_entry = cover.iloc[0]

        # Append buy order
        buy_sell_orders.append({
            'order_id': short_entry['order_id'],
            'symbol': short_entry['symbol'],
            'type': 'BUY',
            'order_time': short_entry['order_time'],
            'quantity': cover_entry['quantity'],
            'netCash': cover_entry['netCash'],
            'commission': cover_entry['commission'],
            'tradeMoney': cover_entry['tradeMoney'],
            'currency': short_entry['currency'],
            'isin': short_entry['isin'],
            'exec_time': short_entry['exec_time'],
            'trade_id': short_entry['trade_id'],
            'transaction_id': short_entry['transaction_id']

        })
        # Append sell order
        buy_sell_orders.append({
            'order_id': cover_entry['order_id'],
            'symbol': cover_entry['symbol'],
            'type': 'SELL',
            'order_time': cover_entry['order_time'],
            'quantity': short_entry['quantity'],
            'netCash': short_entry['netCash'],
            'commission': short_entry['commission'],
            'tradeMoney': short_entry['tradeMoney'],
            'currency': cover_entry['currency'],
            'isin': cover_entry['isin'],
            'exec_time': cover_entry['exec_time'],
            'trade_id': short_entry['trade_id'],
            'transaction_id': short_entry['transaction_id']
        })

    return pd.DataFrame(buy_sell_orders)


def create_pp_dataframe(df):
    note = lambda row: (
            f"Trade-ID: {row['trade_id']} | Transaction-ID: {row['transaction_id']} | Type: "
            + ("Short (open)" if row['type'] == 'BUY' else "Cover (close)")
    )

    pd_df = pd.DataFrame()
    pd_df['date'] = df['exec_time'].dt.date
    pd_df['type'] = df['type']
    pd_df['time'] = df['exec_time'].dt.time
    pd_df['fees'] = df['commission']
    pd_df['value'] = df['netCash']
    pd_df['shares'] = df['quantity']
    pd_df['ticker'] = df['symbol']
    pd_df['currency'] = df['currency']
    pd_df['currencyGross'] = df['currency']
    pd_df['isin'] = df['isin']
    pd_df['note'] = df.apply(note, axis=1)

    return pd_df


def filter_short_cover_types(input_file):
    tree = ET.parse(input_file)
    trades_elem = tree.getroot().find(".//Trades")
    for trade_elem in tree.getroot().findall(".//Trades/Trade"):
        sell = trade_elem.attrib["buySell"]
        indicator = trade_elem.attrib["openCloseIndicator"]
        if determine_trade_type(sell, indicator) in {"SHORT", "COVER"}:
            trades_elem.remove(trade_elem)
    return tree


def main():
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_colwidth', None)
    pd.set_option('display.width', None)

    parser = argparse.ArgumentParser(description='Merge iBRKR trades and change SHORT COVER to mirror inverted BUY / SELL')
    parser.add_argument('-f', '--files', nargs='+', help='iBKR flex xml files')
    parser.add_argument('-o', '--output', help='Portfolio performance csv output file', required=True)
    args = parser.parse_args()

    trades = [trade for xml_file in args.files for trade in parse_ib_data_xml(xml_file)]

    df_trades = pd.DataFrame(trades).astype(
        {
            'order_id': 'int',
            'quantity': 'int',
            'netCash': 'float',
            'commission': 'float',
            'tradeMoney': 'float'
        })

    df_trades = df_trades[(df_trades['type'] == 'SHORT') | (df_trades['type'] == 'COVER')]
    agg_df = aggregate_trades(df_trades)
    converted_orders = convert_short_cover2buy_sell_orders(agg_df)
    print("Aggregated orders:")
    print(agg_df)
    print("\nConverted orders:")
    print(converted_orders)
    print("\n")
    print(f"Write csv file for portfolio performance import to {args.output}")
    create_pp_dataframe(converted_orders).to_csv(args.output, sep=';', index=False, float_format='%.2f', decimal=',')

    for xml_file in args.files:
        output_file = xml_file.replace(".xml", "_filtered.xml")
        print(f"Saving consolidated xml file  to {output_file}")
        new_tree = filter_short_cover_types(xml_file)
        new_tree.write(output_file, encoding='utf-8', xml_declaration=True)


if __name__ == '__main__':
    main()
