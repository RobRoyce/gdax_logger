# gdax-logger
A logger for the GDAX Cryptocurrency Exchange

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Getting Started
Simply download or clone this repo and run `logger.py`.

You might also need to install additional dependencies. I recommend using the `Anaconda3` library [which you can find here](https://www.anaconda.com/download/). It contains many of the packages required to run the logger. You should also install `websocket-client`

If you would like the script to run in the background or on a server, I suggest running the following bash command:
```
nohup python3 logger.py >> stdout.log &
```

Otherwise you can run it in the foreground:
```
python3 logger.py
```

# FAQ
### What is it?
gdax-logger is a script that allows you to establish a direct connection to GDAX and download all of the data relating to a particular cryptocurrency.

Once data is retrieved via websocket, the `LoggerHandler` parses the data and stores it into two SQLite3 databases (one for the Ticker, one for the OrderBook's).

For more detailed information on terms like Ticker, OrderBook, and websocket, please view the [GDAX API Website](https://docs.gdax.com).

### How is data stored?
The Ticker is a simple row of data, and hence requires no special handling. Once Ticker data is received, it is writ directly to database.

On the other hand, the OrderBook is complex. It represents _all_ of the live transactions on GDAX at any given moment. Special handling is required to guarantee integrity of the data. We utilize a segment tree to store and query volume. Special locking is implemented to guarantee updates do not disturb existing queries that have not finished yet. A background (daemon) thread is established at startup and continues to query all existing OrderBook's at approximately 1 second intervals.

### Can I choose which symbols (products) I want to log?
Yes. But this currently requires that you manually go through the code and change them. By default, the logger will pull and save 'BTC-USD', 'ETH-USD', 'LTC-USD', and 'BCH-USD'. I will make this process much easier in future versions.

# Slack support!
I've incorperated Slack messaging into the logger. If you'd like to receive updates about the logger's progress via slack, now you can! Simply change the following variables in `LoggerHandler.py`:
    -`self.__post_to_slack = True`
    -`self.__slack_url = 'www.your.slack.api.url/here'`
Once enabled, any error regarding the database is automatically sent to your personal slack channel.
[See more here about Slack integration](https://get.slack.help/hc/en-us/articles/215770388-Create-and-regenerate-API-tokens) 

### More to come...