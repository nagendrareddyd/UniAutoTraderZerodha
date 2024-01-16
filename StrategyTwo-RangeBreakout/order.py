class Order:
    def __init__(self, tradingsymbol, transaction_type, instrument_token, quantity, strategycode, orderid, status, averagePrice) -> None:
        self.tradingsymbol = tradingsymbol
        self.transaction_type = transaction_type
        self.instrument_token = instrument_token
        self.quantity = quantity
        self.strategycode = strategycode
        self.orderid = orderid
        self.status = status
        self.averagePrice = averagePrice
        pass