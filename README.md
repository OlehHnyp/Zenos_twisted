# Currency rates

It is based on python 2.7 and twisted framework.

In order to use:
- clone this repository
- create new branch and checkout it
- run "git pull origin currency_api"
- install requirements.txt
- add api url into server.py as EXTERNAL_SERVER_URL
- run "python2 server.py"
- run "python2 client.py code1/code2 code3/code4" (Where code1,code2...  are currency codes. See supportedCurrencies.txt. Add as many code pairs as you want.)

All client received data is stored in clientData repository.

Server data(buffer) is stored in serverData.

External API is used only if server buffer doesn't store valid data.