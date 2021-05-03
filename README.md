# s21-team10-project

### How to use:

0. Requirements: [pypokedex](https://pypi.org/project/pypokedex/), tensorflow, jupyter. If you wish to run without collecting your own data, extract replays.zip in the same directory as the rest of the files. 

1. Scrape replays using scrapeReplay.py You need to have a scrape folder present, and it will put up to 50 of the most recent replays in that folder. 

2. Run replay.py to convert downloaded replays into vectors. You need to have scrape-out and scrape-done. Any files left in the scrape folder had an error associated with them. This is fine as I chose to ignore a few things.

3. Run bot.ipny in Jupyter Notebooks. Run the necessary code blocks as stated. Code block 2 is only necessary if you are using a GPU for training your own network. Do read through the markdown comments on various blocks for instructions on what you need to do as a user. 
