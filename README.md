# gdax-logger
A logger for the GDAX Cryptocurrency Exchange

> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Getting Started
I am working on pip support. In the mean time, you can simply download or clone this repo and run `gdax_ticker_logger.py`.

Along with this repo, you might need to install additional dependencies. I recommend using the `Anaconda3` library [which you can find here](https://www.anaconda.com/download/), which contains many of the packages used here. You should also install `websocket-client`

If you would like the script to run in the background or on a server, I suggest running the following bash command:
```
nohup python3 gdax_ticker_logger.py >> stdout.log &
```

Otherwise you can run it in the foreground:
```
python3 gdax_ticker_logger.py
```
### Ticker Logger
The ticker logger retrieves updates directly from GDAX over a websocket connection. Each update contains a JSON message that is deserialized and stored in a CSV. A new CSV is generated at the beginning of each day (12:00a GDAX Server Time).

### CSV Utility
Once you've retrieved log data and want to start using it, you can take advantage of the csv_utility.py script. This script will separate the various crypto products into their own CSV's for further analysis. It also produces a utility log that displays potentially important information regarding the data that was retrieved.

I will continue to work on this portion of the gdax-logger project in the future.

### TODO
- Add order book logging
- Add level 2 logging
- Improve the CSV utility with relevant statistic analysis
- Improve the documentation
