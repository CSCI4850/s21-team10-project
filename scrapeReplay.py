import wget, codecs, os, urllib.request, fileinput, sys, datetime, time, json

url = "https://replay.pokemonshowdown.com/search/?format=gen8ou"
# you might be fine without these
key = "" # put your key here as a string
agent = "" # put your own user agent here
cookie = "__cfduid=" + key

def replaceAll(file, searchExps, replaceExps):
    # if there is just a single string
    if (type(searchExps) != type([1])):
        for line in fileinput.input(file, inplace=1):
            if searchExps in line:
                line = line.replace(searchExps,replaceExps)
            sys.stdout.write(line)
    else:
        for x in range(len(searchExps)):
            for line in fileinput.input(file, inplace=1):
                if searchExps[x] in line:
                    line = line.replace(searchExps[x], replaceExps[x])
                sys.stdout.write(line)

def getPlayers(filename):
    with open(filename, "r") as fp:
        line = fp.readline()
        names = json.loads(line)
    p1 = names['p1']
    p2 = names['p2']
    return p1, p2

def main():
    req = urllib.request.Request(url)
    req.add_header("User-Agent", agent)
    # get this from cookies, I don't think it's important
    req.add_header("Cookie", cookie)
    
    with urllib.request.urlopen(req) as fh:
        with open("scrape/test.html", "wb") as fp:
            fp.write(fh.read())
    
    with codecs.open("scrape/test.html", 'r', "utf8") as fp:
        line = fp.readline()
        i = 0
        while (line):
            if ("gen8ou-" in line):
                temp = line.split("<li>")[1].split(" ")[1][6:-1]
                localPath = "scrape/" + temp + "-c.json"
                if (os.path.isfile(localPath)):
                    pass
                else:
                    newUrl = "http://replay.pokemonshowdown.com" + temp + ".json"
                    print(newUrl)
                    newReq = urllib.request.Request(newUrl)
                    newReq.add_header("User-Agent", agent)
                    newReq.add_header("Cookie", cookie)
                    with urllib.request.urlopen(newReq) as fh:
                        with open(localPath, 'wb') as fpt:
                            fpt.write(fh.read())
                    p1, p2 = getPlayers(localPath)
                    replaceAll(localPath, ["\\n", p1, p2], ["\n", "Player1", "Player2"])
                
            line = fp.readline()

main()
import datetime
timestamp = time.time()
value = datetime.datetime.fromtimestamp(timestamp)
print(datetime.datetime.fromtimestamp(timestamp).isoformat())