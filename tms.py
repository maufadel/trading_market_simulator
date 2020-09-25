import alpaca_trade_api as alpaca
import numpy as np
import pandas as pd
import sys
import os

class Market:
    '''This class automatically downloads the data for the provided symbols from Alpaca,
    and simulates the pass of time during a day by providing 1 minute barsets with its method next_barset().'''
    
    def __init__(self, symbols, alpaca_key_id, alpaca_secret_key, date = None):
        '''
        Initiates a market with symbols and for a given date.

        :param str list symbols: Symbols that will be included in the market, e.g.: [AAPL, GOOG, QQQ].
        :param datetime date: Date to be simulated by market.
        :return: the market object to be queried for bars.
        :rtype: Market.
        '''
        # TODO: set alpaca credentials as input params.
        self._api = alpaca.REST(key_id = alpaca_key_id, 
                                secret_key = alpaca_secret_key,
                                base_url = 'https://paper-api.alpaca.markets')
        self.symbols = symbols
        self.load_day(date)
        
    def load_day(self, date=None):
        '''
        Load data for the indicated date.

        :param: datetime date: Date for market data.
        '''
        self._bars = []

        if date is None:
            date = pd.Timestamp.now(tz='America/New_York').floor('1d')
        else:
            date = date.tz_convert('America/New_York').floor('1d')
        market_open = date.replace(hour=9, minute=30)
        market_close = date.replace(hour=16, minute=0)
        today = date.isoformat()
        tomorrow = (date + pd.Timedelta('1day')).isoformat()
        data = self._api.get_barset(self.symbols, '1Min', start=today, end=tomorrow).df
        bars = data[market_open:market_close]
        self._bars = bars
        self.i = 0
        
    def next_barset(self):
        '''
        Simulates the pass of a minute, returning next barset.

        :return: a barset with open, high, low, close columns for each symbol in market.
        :rtype: barset.
        '''
        if self.i >= len(self._bars.index):
            return None
        
        new_bar = self._bars.loc[self._bars.index[self.i]]
        self.i = self.i+1
        
        return new_bar
    
    def curr_barset(self):
        '''
        Returns current barset.

        :return: a barset with open, high, low, close columns for each symbol in market.
        :rtype: barset.
        '''
        if self.i >= len(self._bars.index):
            return None
        
        return self._bars.loc[self._bars.index[self.i]]
    
    def reset(self, date=None):
        '''
        If date is None, reset time of day to market opening time. If date is not None, 
        change market date at market opening time.

        :param datetime date: Date to be simulated by market.
        '''
        if date is not None:
            # If a date was given, we load the data for that day.
            load_day(date)
        else:
            # If no date was given, we just go back to market opening.
            self.i = 0
        
        
class Asset:
    '''
    Defines a market asset: a symbol and its spread in points.
    '''
    def __init__(self, symbol, spread):
        '''
        Initiates a market asset defined by its symbol and its spread.

        :param str symbol: Symbol or ticker that represents the asset in the market, e.g.: AAPL, GOOG, QQQ.
        :param float spread: Spread of the asset in points, e.g.: 2.4.
        :return: a market asset.
        :rtype: Asset.
        '''
        self.symbol = symbol
        self.spread = spread
        
        
class Broker:
    '''Creates a broker that allows to trade the market assets for a given date.
    It provides all the functionality relative to a broker: opening accounts, deposit to account,
    provide information about assets (through its market), opening and close of positions.'''
    def __init__(self, assets, alpaca_key_id, alpaca_secret_key, date = None):
        '''
        Initiates a Broker to trade assets during a day. Date can be changed on-demand, but only data for a
        day is managed at once.

        :param Asset assets: List of market assets to be traded.
        :param datetime date: Date to be simulated by market, by default today. 
        :return: broker.
        :rtype: Broker.
        '''
        self.assets = assets
        self.assets_spread = {}
        for a in assets:
            self.assets_spread[a.symbol] = a.spread
            
        self.market = Market([a.symbol for a in assets], alpaca_key_id, alpaca_secret_key, date)
        self.accounts = {}
        
        
    def next_timestep(self):
        '''
        Simulates the pass of a minute, returning next barset.

        :return: a barset with open, high, low, close columns for each symbol in market.
        :rtype: barset.
        '''
        # TODO: Check TP and SL of open positions and close them if TP or SL reached.
        return self.market.next_barset()
    
    def curr_barset(self):
        return self.market.curr_barset()
        
        
    def open_account(self, name, initial_deposit):
        '''
        Opens a new account, identified by its name, with the amount indicated in initial_deposit.

        :param: str name: Identifier for the account, necessary to access it afterwards.
        :param: float initial_deposit: initial amount of cash the account will have.
        :raises Exception: if the account name already exists.
        '''
        if self.accounts.get(name):
            raise Exception('Account already exists!')
            
        self.accounts[name] = BrokerAccount(name, initial_deposit)
        
    def get_positions(self, account_name):
        '''
        Returns a list with the positions for the account account_name.

        :param: str account_name: Identifier for the account.
        :raises Exception: if the account name does not exist.
        '''
        if self.accounts.get(account_name) is None:
            raise Exception('Account does not exist!')
            
        return self.accounts.get(account_name).positions
    
    def get_history(self, account_name):
        '''
        Returns a list with the closed positions for the account account_name.

        :param: str account_name: Identifier for the account.
        :raises Exception: if the account name does not exist.
        '''
        if self.accounts.get(account_name) is None:
            raise Exception('Account does not exist!')
            
        return self.accounts.get(account_name).history
        
    def deposit_into_account(self, name, amount):
        '''
        Add the amount indicated to an existing account.

        :param: str name: Identifier for the account.
        :param: float amount: amount of cash to be added to the account.
        :raises Exception: if the account name does not exist.
        '''
        if self.accounts.get(name) is None:
            raise Exception('Account does not exist!')
            
        self.accounts.get(name).available += amount
        
        
    def open_position(self, account_name, symbol, position_type, value, sl=None, tp=None):
        '''
        Opens a position for a symbol and an account.

        :param: str account_name: Identifier for the account.
        :param: str symbol: Symbol to buy/sell.
        :param: str position_type: defines type of position, valid options: 'buy', 'sell'.
        :param: float value: amount in cash to buy/sell of the indicated symbol.
        :param: float sl: stop loss for position.
        :param: float tp: take profit for position.
        :raises Exception: if the account name does not exist.
        :raises Exception: if symbol does not exist.
        :raises Exception: if account does not posses enough money to open position.
        :raises Exception: if type of position is not 'buy' or 'sell'.
        :return: the open position.
        :rtype: Position.
        '''
        # Note: We use price at current close.
        if self.accounts.get(account_name) is None:
            raise Exception('Account does not exist!')
        if self.assets_spread.get(symbol) is None or symbol not in self.market.curr_barset():
            raise Exception('Symbol not in market!')
        if self.accounts.get(account_name).available < value:
            raise Exception('Not enough money available in account!')
        if position_type != 'buy' and position_type != 'sell':
            raise Exception('Position type must be buy or sell!')
            
        open_price = 0
        curr_barset = self.market.curr_barset()
        open_price = curr_barset[symbol]['close']
        
        if position_type == 'buy':
            open_price += self.assets_spread.get(symbol)
            
        units = value/open_price
        pos = Position(symbol, curr_barset.name, position_type, open_price, units, sl, tp)
        
        self.accounts.get(account_name).positions.append(pos)
        self.accounts.get(account_name).available -= value
        return pos
    
    
    def close_positions(self, account_name, symbol, price=None):
        '''
        Closes all of the positions for a given symbol and returns the closed positions.
        If price is None, we close it at the close price of current barset as defined in 
        close_position().

        :param: str account_name: Identifier for the account.
        :param: str symbol: Symbol of the positions to close.
        :param: float price: price in which positions will be closed.
        :return: list of positions closed.
        :rtype: list of Position.
        '''
        
        # TODO: add units param to close part of the positions if needed.
        if self.accounts.get(account_name) is None:
            raise Exception('Account does not exist!')
        if self.assets_spread.get(symbol) is None or symbol not in self.market.curr_barset():
            raise Exception('Symbol not in market!')
            
        # Find positions to close.
        to_close = []
        for p in self.accounts.get(account_name).positions:
            if p.symbol == symbol:
                to_close.append(p)
                
        # Close positions and move them to history.
        for p in to_close:
            self.close_position(account_name, p, price)
            
        return to_close
    
    def close_position(self, account_name, position, price=None):
        '''
        Closes the position. If price is None, we close it at the close price of current barset.

        :param: str account_name: Identifier for the account.
        :param: str symbol: Symbol of the positions to close.
        :param: float price: price in which positions will be closed.
        :return: list of positions closed.
        :rtype: list of Position.
        '''
        if self.accounts.get(account_name) is None:
            raise Exception('Account does not exist!')
        # TODO: check if position is not in account_name positions.
        
        # If price is None, we use the close price for the current barset.
        if price is None:
            curr_barset = self.market.curr_barset()
            price = curr_barset[position.symbol]['close']
            
        position.close_price = price
        if position.position_type == 'sell':
            position.close_price += self.assets_spread.get(position.symbol)
        position.close_date = self.market.curr_barset().name
        self.accounts.get(account_name).positions.remove(position)
        self.accounts.get(account_name).history.append(position)
        self.accounts.get(account_name).available += position.get_valuation(price)
        
        
    def get_account_balance(self, account_name):
        '''
        Returns the available cash for the account account_name.

        :param: str account_name: Identifier for the account.
        :raises Exception: if the account name does not exist.
        '''
        if self.accounts.get(account_name) is None:
            raise Exception('Account does not exist!')
            
        return self.accounts.get(account_name).available
        
    
    def reset(self, date=None):
        '''
        Resets the market data to market opening, if a date is provided it changes the day to that date.
        ATTENTION! If there are any open positions, this method might create inconsistencies.

        :param: datetime date: Date for market data.
        '''
        self.market.reset(date)
                
        
        
class Position:
    '''Represents a position for a symbol in the market.'''
    def __init__(self, symbol, open_date, position_type, open_price, units, 
                 sl=None, tp=None, close_price=None, close_date=None):
        '''
        Creates a position for a symbol.

        :param: str symbol: Symbol to buy/sell.
        :param: datetime open_date: date in which position was opened.
        :param: str position_type: defines type of position, valid options: 'buy', 'sell'.
        :param: float open_price: price of the asset when position was opened.
        :param: float units: amount of asset in position.
        :param: float sl: stop loss for position.
        :param: float tp: take profit for position.
        :param: float close_price: price of the asset when position was closed.
        :param: datetime close_date: date in which position was closed.
        :return: the position.
        :rtype: Position.
        '''
        self.symbol = symbol
        self.open_date = open_date
        self.position_type = position_type
        self.open_price = open_price
        self.units = units
        self.sl = sl
        self.tp = tp
        self.close_price = close_price
        self.close_date = close_date
        
    def get_valuation(self, price):
        '''
        Calculates and returns the valuation of the position at the given price.

        :param: float price: current price of the asset.
        :return: value in cash of the position.
        :rtype: float.
        '''
        return self.units*self.open_price + self.get_profit(price)
    
    def get_profit(self, price):
        '''
        Calculates and returns the profit of the position. If the position is closed, profit
        is calculated using self.close_price, else given price as parameter is used.

        :param: float price: current price of the asset.
        :return: profit generated by position since it was opened (can be negative).
        :rtype: float.
        '''
        if self.close_price is not None:
            price = self.close_price
            
        if self.position_type == 'buy':
            return self.units * (price - self.open_price)
        elif self.position_type == 'sell':
            return self.units * (-price + self.open_price)
        else:
            raise Exception('Operation type not recognized!')
            


class BrokerAccount:
    '''A broker account, identified by its name. It contains date of available cash, open positions 
    and close positions (history).'''
    def __init__(self, name, available, positions=None, history=None):
        '''
        Initiates a BrokerAccount identified by its name and with the given available cash, used to
        open positions. By default, positions and history will be initialized to empty lists.

        :param: str name: Identifier for the account.
        :param: float available: available cash in the account.
        :param: list of Position positions: open positions in account.
        :param: list of Posision history: closed positions of account.
        :return: the account
        :rtype: BrokerAccount.
        '''
        self.name = name
        self.available = available
        
        if positions is None:
            positions = []
        self.positions = positions
        
        if history is None:
            history = []
        self.history = history
        

class Trader:
    # TODO.
    pass
        