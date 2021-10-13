import sys
import os
import json
import csv

from twisted.internet import task
from twisted.internet.protocol import Protocol, ClientFactory


SERVER_HOST = "localhost"
SERVER_PORT = 8123
INTERVAL = 5  # add interval in seconds for obtaining currency pair rate

class CurrencyProtocol(Protocol):

    def connectionMade(self):
        print "Connection made"
        self.startLoop()

    def dataReceived(self, data):
        self.factory.writeIntoFile(data)

    def connectionLost(self, reason):
        print "connection lost", reason

    def startLoop(self):
        """
        Start sending currency request to the server.
        :return: None
        """
        self._sender = task.LoopingCall(self.sendRequest)
        self._sender.start(interval=INTERVAL)

    def sendRequest(self):
        """
        Send a request to the server with currency inside.
        :return: None
        """
        self.transport.write(self.factory.currency)


class CurrencyClientFactory(ClientFactory):

    protocol = CurrencyProtocol

    def __init__(self, currency):
        self.currency = currency
        self.file = "clientData/" + "_".join(currency.split("/")) + ".csv"  # file for storing obtained data
        self.fieldnames = [
            "result",
            "base_code",
            "target_code",
            "conversion_rate",
            "time_last_update_utc",
            "time_last_update_unix",
            "time_next_update_utc",
            "time_next_update_unix",
            "error",
        ]

    def _fileEmptyOrNotExist(self):
        """
        Check if the file is empty or not exists.
        :return: bool
        """
        return not os.path.isfile(self.file) or os.path.getsize(self.file) == 0

    def writeIntoFile(self, data):
        """
        Write data into .csv file.
        :param data: str
        :return: None
        """
        data = json.loads(data)
        with open(self.file, "a+") as f:
            writer = csv.DictWriter(f, fieldnames=self.fieldnames)
            if self._fileEmptyOrNotExist():
                writer.writeheader()
            writer.writerow(data)
            print "writing... ", self.currency, data.get("result") or data.get("error")


def main():
    """
    For each currency create factory and TCP connection, run reactor.
    :return: None
    """
    from twisted.internet import reactor
    for currency in sys.argv[1:]:
        factory = CurrencyClientFactory(currency)
        reactor.connectTCP(SERVER_HOST, SERVER_PORT, factory)
    reactor.run()

if __name__ == "__main__":
    main()
