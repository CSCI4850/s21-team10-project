# Stores a pokemon based on dex number, moves, etc.
# Numbers are all based on known internal IDs

from enum import IntEnum, auto, IntFlag
import copy, codecs, re, os, traceback
import pypokedex as pkd

# debug input and output
# inputCsv = "input.csv"
# outputCsv = "output.csv"

WIN = False
# stores a full battle
class Replay():
    def __init__(self, repJson, csv):
        # throw away the garbage header data as well as other unwanted stuff
        # would be what these two do
        # self.preprocess(fp, out)
        # fp.close()
        # we need codecs because usernames and nicknames can have unicode
        
        # setup labels for the input
        print("Working on:", repJson, end=' ')
        inputCsv = csv + "-in.csv"
        outputCsv = csv + "-out.csv"
        
        with open(inputCsv, "w") as fpw:
            for i in range(2):
                for x in range(6):
                    fpw.write("p{X}HP,p{X}Atk,p{X}Def,p{X}SpA,p{X}SpD,p{X}Spe,p{X}Move1,p{X}PP1,p{X}Move2,p{X}PP2,p{X}Move3,p{X}PP3,p{X}Move4,p{X}PP4,p{X}Ability,".format(X = x))
            fpw.write("terrain,weather,trick room,wonder room,magic room,p1 lead,p1 transform,p1 hazards,p1 volatile,p1 AtkB,p1 DefB,p1 SpAB,p1 SpDB,p1 SpeB,p2 lead, p2 transform,p2 hazards,p2 volatile,p2 AtkB,p2 DefB,p2 SpAB,p2 SpDB,p2 SpeB\n")
        # and setup labels for the output
        with open(outputCsv, "w") as fpw:
            fpw.writelines("p1Move,p1Switch,p2Move,p2Switch\n")
        fp = codecs.open(repJson, 'r', "utf8")
        
        # the first important thing we want is the poke block
        line = fp.readline().strip()
        while (not line.startswith("|team")):
            line = fp.readline().strip()
        
        # |teamsize|pX|int
        team1 = int(line.split('|')[3])
        line = fp.readline().strip()
        team2 = int(line.split('|')[3])
        line = fp.readline().strip()
        
        # just to make sure data isn't scuffed
        while (not line.startswith("|tier")):
            line = fp.readline().strip()
        battle_format = line.split('|')[2]
        if (not battle_format.startswith("[Gen 8] OU")):
            print("Error, not a gen 8 OU replay: ", battle_format)
        
        # now to get the two teams
        line = fp.readline().strip()
        # clearpoke is team preview signal
        # maybe we have a separate net to analyze the preview?
        while (not line.startswith("|clear")):
            line = fp.readline().strip()
        pokemon = []
        poke_str = [[], []]
        temp = []
        
        # |poke|pX|<name>, <gender>|
        # we store the pokemon and the string to make it easier to index later
        for x in range(team1):
            line = fp.readline().strip()
            nameList = line.split('|')[3].split(", ")
            # I have zero idea how to deal with this without rewriting a lot of stuff
            if ("Zoroark" in line):
                print("Error: cannot track Zoroark")
                fp.close()
                os.rename(repJson, repJson.replace("scrape", "scrape-done"))
                return
            if ("Gourgeist" in line):
                print("I'm not making a case for Gourgeist when its raw usage is 3000 in a month")
                fp.close()
                os.rename(repJson, repJson.replace("scrape", "scrape-done"))
                return
            if (len(nameList) == 1):
                if (nameList[0].startswith("Silvally")):
                    temp.append(Pokemon("Silvally", Gender.G))
                    nameList[0] = "Silvally"
                temp.append(Pokemon(nameList[0], Gender.G))
                poke_str[0].append(nameList[0].strip())
            else:
                if (nameList[0].startswith("Urshifu")):
                    temp.append(Pokemon("Urshifu-Rapid-Strike", nameList[1]))
                    nameList[0] = "Urshifu-Rapid-Strike" # is it just urshifu or this
                else:
                    temp.append(Pokemon(nameList[0], nameList[1]))
                poke_str[0].append(nameList[0].strip())
        pokemon.append(temp)
        
        temp = []

        for x in range(team2):
            line = fp.readline().strip()
            nameList = line.split('|')[3].split(", ")
            if ("Zoroark" in line):
                print("Error: cannot track Zoroark")
                fp.close()
                os.rename(repJson, repJson.replace("scrape", "scrape-done"))
                return
            if ("Gourgeist" in line):
                print("I'm not making a case for Gourgeist when its raw usage is 3000 in a month")
                fp.close()
                os.rename(repJson, repJson.replace("scrape", "scrape-done"))
                return
            if (len(nameList) == 1):
                if (nameList[0].startswith("Silvally")):
                    temp.append(Pokemon("Silvally", Gender.G))
                    nameList[0] = "Silvally"
                temp.append(Pokemon(nameList[0], Gender.G))
                poke_str[1].append(nameList[0].strip())
            else:
                if (nameList[0].startswith("Urshifu")):
                    temp.append(Pokemon("Urshifu-Rapid-Strike", nameList[1]))
                    nameList[0] = "Urshifu-Rapid-Strike"
                else:
                    temp.append(Pokemon(nameList[0], nameList[1]))
                poke_str[1].append(nameList[0].strip())
        pokemon.append(temp)
        global WIN
        
        # somewhere here should be where we analyze the team preview
        # it can be as simple as taking their dex numbers and going off leads usage
        line = fp.readline().strip()
        while (not line.startswith("|teampreview")):
            if ((line.startswith("|win")) or (line.startswith("|tie"))):
                WIN = True
            line = fp.readline().strip()
        
        turns = []
        turns.append(Turn(fp, pokemon, poke_str, None))
        turns[0].GenerateFiles(inputCsv, outputCsv)
        line = fp.readline().strip()
        i = 0
        
        # print(poke_str)
        
        while (not (WIN)):
            #print("Turn:", i)
            turns.append(Turn(fp, pokemon, poke_str, turns[i]))
            turns[i + 1].GenerateFiles(inputCsv, outputCsv)
            i += 1
        
        print("Won at turn:", i)
        WIN = False
        fp.close()
        os.rename(repJson, repJson.replace("scrape", "scrape-done"))



####################################################################################
# Stores the state of one turn                                                     #
# a turn needs to know which moves are picked (either an actual move or switch)    #
# how much damage                                                                  #
# who moved first                                                                  #
# abilities that went off?                                                         #
# the turn id because why not                                                      #
# whether or not crit                                                              #
# weather/terrain                                                                  #
# maybe the super effective flag too?                                              #
####################################################################################
class Turn():
    # teampreview turn
    def __init__(self, fp, pokemon, poke_str, prev_turn):
        self.debugStr = ""
        # first turns always start with a start instruction 
        # followed by switch instructions
        
        # vars:
        # p1Lead/p2Lead: int containing the index of the lead
        # first: who went first this turn
        # fields: the list in order of currently active fields
        global WIN
        if (prev_turn is None):
            self.p1Hazards = Hazards_List.NoHazards
            self.p2Hazards = Hazards_List.NoHazards
            self.p1Volatile = Volatile_List.NoVolatile
            self.p2Volatile = Volatile_List.NoVolatile
            self.p1Boosts = [0, 0, 0, 0, 0, 0, 0]
            self.p2Boosts = [0, 0, 0, 0, 0, 0, 0]
            self.p1Crit = False
            self.p2Crit = False
            self.isTurn0 = True
            self.insOrder = []
            self.p1Party = copy.deepcopy(pokemon[0])
            self.p2Party = copy.deepcopy(pokemon[1])
            self.terrain = Terrain_List.NoTerrain
            self.weather = Weather_List.NoWeather
            self.trickRoom = False
            self.wonderRoom = False
            self.magicRoom = False
            self.gravity = False
            self.p1SwitchFlag = False
            self.p2SwitchFlag = False
            
            line = fp.readline().strip()
            while (not line.startswith("|start")): # first turn signal
                line = fp.readline().strip()
                if ((line.startswith("|win")) or (line.startswith("|tie"))):
                    WIN = True
                    return
            lead = fp.readline().split("|")
            
            # leads are not determmined by speed
            # but we might as well do it this way
            if (lead[2][1] == '1'):
                self.first = 1
                if (lead[3].split(",")[0].startswith("Silvally")):
                    for x in range(len(poke_str[0])):
                        if poke_str[0][x].startswith("Silvally"):
                            self.p1Lead = x
                else:
                    self.p1Lead = poke_str[0].index(lead[3].split(",")[0])
                lead = fp.readline().split("|")
                self.p2Lead = poke_str[1].index(lead[3].split(",")[0])
            else:
                self.first = 2
                if (lead[3].split(",")[0].startswith("Silvally")):
                    for x in range(len(poke_str[1])):
                        if poke_str[1][x].startswith("Silvally"):
                            self.p1Lead = x
                else:
                    self.p2Lead = poke_str[1].index(lead[3].split(",")[0])
                lead = fp.readline().split("|")
                self.p1Lead = poke_str[0].index(lead[3].split(",")[0])
            
            self.p1Switch = self.p1Lead
            self.p2Switch = self.p2Lead
            
            line = fp.readline().strip()
            # since turn 0 should only do field effects, we only check for them
            while (not line.startswith("|turn")):
                info = line.split("|")
                field_str = info[2].replace(" ", "").replace("move:", "").strip()
                if ((line.startswith("|win")) or (line.startswith("|tie"))):
                    WIN = True
                    return
                if (line.startswith("|-fieldstart")):
                    # we need some logic here to determine what type of field
                    # trick and wonder rooms cannot come out turn 0 but c/p code
                    if field_str.startswith("Trick"):
                        self.rickRoom = True
                    elif field_str.startswith("Wonder"):
                        self.wonderRoom = True
                    elif field_str.startswith("Gravity"):
                        self.gravity = True
                    elif field_str.endswith("Terrain"):
                        self.terrain = Terrain_List[field_str]
                    elif field_str.startswith("Magic"):
                        self.magicRoom = True
                    else: # error?
                        print("Unknown field start:", line)
                        exit()
                    if (info[4][6] == '1'): # [4][6] is the player number
                        ability_str = info[3][15:].replace(" ", "")
                        self.p1Party[self.p1Lead].ability = Ability_List[ability_str]
                    else:
                        ability_str = info[3][15:].replace(" ", "")
                        self.p2Party[self.p2Lead].ability = Ability_List[ability_str]
                elif (line.startswith("|-weather")):
                    self.weather = Weather_List[field_str]
                # intimidate and friends
                elif (line.startswith("|-ability")):
                    if (info[2][1] == '1'):
                        self.p1Party[self.p1Lead].ability = Ability_List[info[3].replace(" ","")]
                    else:
                        self.p2Party[self.p2Lead].ability = Ability_List[info[3].replace(" ","")]
                elif (line.startswith("|-unboost")):
                    stat = Stat_List[info[3] + 'S']
                    if (info[2][1] == '1'):
                        self.p1Boosts[stat] += int(info[4]) * -1
                    else:
                        self.p2Boosts[stat] += int(info[4]) * -1
                elif (line.startswith("|-item")):
                    if (info[2][1] == '1'):
                        self.p1Party[self.p1Lead].item = info[3].replace(" ", "")
                    else:
                        self.p2Party[self.p2Lead].item = info[3].replace(" ", "")
                        
                elif (line.startswith("|-boost")):
                    stat = Stat_List[info[3] + 'S']
                    if (info[2][1] == '1'):
                        self.p1Boosts[stat] += int(info[4])
                    else:
                        self.p2Boosts[stat] += int(info[4])
                        
                elif (line.startswith("|-enditem")):
                    if (info[2][1] == '1'):
                        self.p1Party[self.p1Lead].item = "None"
                    else:
                        self.p2Party[self.p2Lead].item = "None"
                elif (line.startswith("|-fail")):
                    pass
                elif (line.startswith("|-transform")):
                    if (info[2][1] == '1'):
                        self.p1Party[self.p1Lead].ability = Ability_List.Imposter
                        self.p1Party[self.p1Lead].Transformed = True
                    else:
                        self.p1Party[self.p1Lead].ability = Ability_List.Imposter
                        self.p2Party[self.p2Lead].Transformed = True
                # white herb activation from intimidate
                elif (line.startswith("|-clearnegativeboost")):
                    if (info[2][1] == '1'):
                        for x in range(7):
                            if (self.p1Boosts[x] < 0):
                                self.p1Boosts[x] = 0
                    else:
                        for x in range(7):
                            if (self.p1Boosts[x] < 0):
                                self.p1Boosts[x] = 0

                    
                else:
                    print("Unknown turn 0 action:", line)
                    exit()
                line = fp.readline().strip()
        # this is for every actual turn
        else:
            # first get the previous turn leads and other stuff
            if (prev_turn.p1SwitchFlag):
                self.p1Lead = prev_turn.p1Switch
            else:
                self.p1Lead = prev_turn.p1Lead
            if (prev_turn.p2SwitchFlag):
                self.p2Lead = prev_turn.p2Switch
            else:
                self.p2Lead = prev_turn.p2Lead
            self.p1Switch = -1
            self.p1SwitchFlag = False
            self.p2Switch = -1
            self.p2SwitchFlag = False

            self.p1Hazards = prev_turn.p1Hazards 
            self.p2Hazards = prev_turn.p2Hazards 
            self.p1Volatile = prev_turn.p1Volatile
            self.p2Volatile = prev_turn.p2Volatile
            self.p1Boosts = prev_turn.p1Boosts
            self.p2Boosts = prev_turn.p2Boosts
            self.p1Crit = False
            self.p2Crit = False
            self.isTurn0 = False
            self.insOrder = []
            self.p1Party = copy.deepcopy(prev_turn.p1Party)
            self.p2Party = copy.deepcopy(prev_turn.p2Party)
            self.terrain = prev_turn.terrain
            self.weather = prev_turn.weather
            self.trickRoom = prev_turn.trickRoom
            self.wonderRoom = prev_turn.wonderRoom
            self.magicRoom = prev_turn.magicRoom
            self.gravity = prev_turn.gravity
            
            # index of the move
            self.p1Move = 0
            self.p2Move = 0
            
            
            #print("p1\n", self.p1Party[self.p1Lead])
            #print("p2\n", self.p2Party[self.p2Lead])
            
            
            line = fp.readline().strip()
            while ((line == "|") or (line == "")):
                line = fp.readline().strip()
            # print(line)
            line = line.split("|")
            
            # loop to check every instruction in a turn
            # not too important but major actions do not have a prefix
            # minor actions have a "-" prefix
            # https://github.com/smogon/pokemon-showdown/blob/master/sim/SIM-PROTOCOL.md
            while (not line[1].startswith("turn")):
                # win con
                if ((line[1].startswith("win")) or (line[1].startswith("tie"))):
                    WIN = True
                    return
                self.insOrder.append(line[1])
                # process a move
                # this involves adding the move if needed
                # and incrementing the pp value for that move
                # right now it ignores pressure, which should be fixed
                if (line[1].startswith("move")):
                    theMove = Move_List[line[3].replace(" ", "").replace("-", "").replace("\'", "")]
                    if (theMove == Move_List.Struggle):
                        break
                    if (line[2][1] == '1'):
                        if (len(line) > 5):
                            if ("ability" in line[5]):
                                self.p1Party[self.p1Lead].Ability = Ability_List[line[5].split(": ")[1].replace(" ", "")]
                            break
                        thePokemon = self.p1Party[self.p1Lead]
                        thePokemon = self.p1Party[self.p1Lead]
                        thePokemon.AddMove(theMove)
                    # player 2
                    else:
                        if (len(line) > 5):
                            if ("ability" in line[5]):
                                self.p2Party[self.p2Lead].Ability = Ability_List[line[5].split(": ")[1].replace(" ", "")]
                            break
                        thePokemon = self.p2Party[self.p2Lead]
                        thePokemon.AddMove(theMove)
                        
                # switch lead logic
                elif (line[1].startswith("switch")):
                    if (line[2][1] == '1'):
                        if (line[3].split(",")[0].startswith("Silvally")):
                            for x in range(len(poke_str[0])):
                                if poke_str[0][x].startswith("Silvally"):
                                    type = line[3].split("-")[1]
                                    self.p1Party[x].type = [Types[type.lower().replace(", shiny", "")]]
                                    self.p1Switch = x
                                    self.p1Lead = x
                        elif (line[3].split(",")[0].startswith("Urshifu")):
                            for x in range(len(poke_str[0])):
                                if poke_str[0][x].startswith("Urshifu"):
                                    self.p1Switch = x
                                    self.p1Lead = x
                                    break
                        else:
                            if (self.p1Party[self.p1Lead].Transformed):
                                self.p1Party[self.p1Lead].Transformed = False
                                self.p1Party[self.p1Lead].ResetTransformMoves()
                            if ("Busted" in line[3]):
                                x = poke_str[0].index(line[3].split(",")[0].replace("-Busted", ""))
                            else:
                                x = poke_str[0].index(line[3].split(",")[0])
                            self.p1Switch = x
                            self.p1Lead = x
                        self.p1Boosts = [0, 0, 0, 0, 0, 0, 0]
                        self.p1SwitchFlag = True
                    else:
                        if (line[3].split(",")[0].startswith("Silvally")):
                            for x in range(len(poke_str[1])):
                                if poke_str[1][x].startswith("Silvally"):
                                    type = line[3].split("-")[1]
                                    self.p2Party[x].type = [Types[type.lower().replace(", shiny", "")]]
                                    self.p2Switch = x
                                    self.p2Lead = x
                        elif (line[3].split(",")[0].startswith("Urshifu")):
                            for x in range(len(poke_str[1])):
                                if poke_str[1][x].startswith("Urshifu"):
                                    self.p2Switch = x
                                    self.p2Lead = x
                                    break
                        else:
                            if (self.p1Party[self.p1Lead].Transformed):
                                self.p1Party[self.p1Lead].Transformed = False
                                self.p1Party[self.p1Lead].ResetTransformMoves()
                            if ("Busted" in line[3]):
                                x = poke_str[1].index(line[3].split(",")[0].replace("-Busted", ""))
                            else:
                                x = poke_str[1].index(line[3].split(",")[0])
                            self.p2Switch = x
                            self.p2Lead = x
                        self.p2Boosts = [0, 0, 0, 0, 0, 0, 0]
                        self.p2SwitchFlag = True

                # handles a permanent change like megas
                # this is probably unused for OU
                elif (line[1].startswith("detailschange")):
                    pass
                
                # illusion reveal
                # effectively useless
                elif (line[1].startswith("replace")):
                    pass
                
                # double battle only
                elif (line[1].startswith("swap")):
                    pass
                    
                # the move could not be used
                # from para and disable
                elif (line[1].startswith("cant")):
                    pass
                    
                elif (line[1].startswith("drag")):
                    if (line[2][1] == '1'):
                        if (line[3].split(",")[0].startswith("Silvally")):
                            for x in range(len(poke_str[0])):
                                if poke_str[0][x].startswith("Silvally"):
                                    type = line[3].split("-")[1]
                                    self.p1Party[x].type = [Types[type.lower()]]
                                    self.p1Switch = x
                        else:
                            self.p1Switch = poke_str[0].index(line[3].split(",")[0])
                        self.p1Boosts = [0, 0, 0, 0, 0, 0, 0]
                        self.p1SwitchFlag = True
                    else:
                        if (line[3].split(",")[0].startswith("Silvally")):
                            for x in range(len(poke_str[1])):
                                if poke_str[1][x].startswith("Silvally"):
                                    type = line[3].split("-")[1]
                                    self.p2Party[x].type = [Types[type.lower()]]
                                    self.p1Switch = x
                        else:
                            self.p2Switch = poke_str[1].index(line[3].split(",")[0])
                        self.p2Boosts = [0, 0, 0, 0, 0, 0, 0]
                        self.p2SwitchFlag = True

                # something died
                # I think this can be skipped
                elif (line[1].startswith("faint")):
                    pass

                elif (line[1].startswith("raw")):
                    pass

                elif (line[1].startswith("c")):
                    pass

                # idk where this gets used, it's not block
                # can probably be skipped
                elif (line[1].startswith("-fail")):
                    pass

                # like fail but not
                # can probably be skipped
                elif (line[1].startswith("-block")):
                    pass

                # something fainted before the action
                # usually recoil death
                # can be skipped
                elif (line[1].startswith("-notarget")):
                    pass

                # your will-o-wisp didn't land again
                # can probably be skipped
                elif (line[1].startswith("-miss")):
                    pass

                # inflict damage
                elif (line[1].startswith("-damage")):
                    if (line[2][1] == '1'):
                        if ("fnt" in line[3]):
                            self.p1Party[self.p1Lead].HP = 0
                        else:
                            try:
                                self.p1Party[self.p1Lead].HP = int(line[3].split("\\")[0])
                            except:
                                self.p1Party[self.p1Lead].HP = int(line[3].split(" ")[0])
                    else:
                        if ("fnt" in line[3]):
                            self.p1Party[self.p1Lead].HP = 0
                        else:
                            try:
                                self.p2Party[self.p2Lead].HP = int(line[3].split("\\")[0])
                            except:
                                self.p2Party[self.p2Lead].HP = int(line[3].split(" ")[0])

                # inverse inflict damage
                elif (line[1].startswith("-heal")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].HP = int(line[3].split("\\")[0])
                    else:
                        self.p2Party[self.p2Lead].HP = int(line[3].split("\\")[0])

                # ...what
                # maybe it's used for healing wish and clones?
                elif (line[1].startswith("-sethp")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].HP = int(line[3].split("\\")[0])
                    else:
                        self.p2Party[self.p2Lead].HP = int(line[3].split("\\")[0])

                # inflict a status
                elif (line[1].startswith("-status")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].Status = Status_List[line[3]]
                    else:
                        self.p2Party[self.p2Lead].Status = Status_List[line[3]]

                # basically just eating a berry?
                elif (line[1].startswith("-curestatus")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].Status = Status_List.non
                    else:
                        self.p2Party[self.p2Lead].Status = Status_List.non

                # heal bell and aroma
                elif (line[1].startswith("-cureteam")):
                    if (line[2][1] == '1'):
                        for x in range(len(self.p1Party)):
                            self.p1Party[x].Status = Status_List.non
                    else:
                        for x in range(len(self.p2Party)):
                            self.p2Party[x].Status = Status_List.non

                # stat boosts
                elif (line[1].startswith("-boost")):
                    stat = Stat_List[line[3] + 'S']
                    if (line[2][1] == '1'):
                        self.p1Boosts[stat] += int(line[4])
                    else:
                        self.p2Boosts[stat] += int(line[4])

                # inverse stat boosts
                elif (line[1].startswith("-unboost")):
                    stat = Stat_List[line[3] + 'S']
                    if (line[2][1] == '1'):
                        self.p1Boosts[stat] += int(line[4]) * -1
                    else:
                        self.p2Boosts[stat] += int(line[4]) * -1

                # trade stat boosts between two pokemon
                # pretty sure this doesn't matter
                elif (line[1].startswith("-swapboost")):
                    pass

                # topsy-turvy
                elif (line[1].startswith("-invertboost")):
                    if (line[2][1] == '1'):
                        for x in range(len(self.p1Party)):
                            self.p1Boosts[x] *= -1
                    else:
                        for x in range(len(self.p2Party)):
                            self.p2Boosts[x] *= -1

                # clear smog
                elif (line[1].startswith("-clearboost")):
                    if (line[2][1] == '1'):
                        for x in range(len(self.p1Party)):
                            self.p1Boosts[x] = 0
                    else:
                        for x in range(len(self.p2Party)):
                            self.p2Boosts[x] = 0

                # haze clears the whole field
                elif (line[1].startswith("-clearallboost")):
                    self.p1Boosts = [0, 0, 0, 0, 0, 0, 0]
                    self.p2Boosts = [0, 0, 0, 0, 0, 0, 0]

                # spec thief logic, unused I think
                elif (line[1].startswith("-clearpositiveboost")):
                    if (line[2][1] == '1'):
                        for x in range(7):
                            if (self.p1Boosts[x] > 0):
                                self.p1Boosts[x] = 0
                    else:
                        for x in range(7):
                            if (self.p1Boosts[x] > 0):
                                self.p1Boosts[x] = 0

                elif (line[1].startswith("-clearnegativeboost")):
                    if (line[2][1] == '1'):
                        for x in range(7):
                            if (self.p1Boosts[x] < 0):
                                self.p1Boosts[x] = 0
                    else:
                        for x in range(7):
                            if (self.p1Boosts[x] < 0):
                                self.p1Boosts[x] = 0

                # unused in gen 8?
                elif (line[1].startswith("-copyboost")):
                    pass

                # rain and stuff
                elif (line[1].startswith("-weather")):
                    self.weather = Weather_List[line[2].replace(" ", "").replace("none", "NoWeather")]

                # terrain/room start
                elif (line[1].startswith("-fieldstart")):
                    field_str = line[2].replace("move:", "").strip()
                    if field_str.startswith("Trick"):
                        self.rickRoom = True
                    elif field_str.startswith("Wonder"):
                        self.wonderRoom = True
                    elif field_str.startswith("Gravity"):
                        self.gravity = True
                    elif field_str.endswith("Terrain"):
                        self.terrain = Terrain_List[field_str.replace(" ", "")]
                    elif field_str.startswith("Magic"):
                        self.magicRoom = True
                    else: # error?
                        print("Unknown field start:", line)
                        exit()
                    # this sets the ability based on fields
                    # might be inaccurate
                    # if (info[4][6] == '1'): # [4][6] is the player number
                    #     ability_str = info[3][15:].replace(" ", "")
                    #     self.p1Party[self.p1Lead].ability = Ability_List[ability_str]
                    # else:
                    #     ability_str = info[3][15:].replace(" ", "")
                    #     self.p2Party[self.p2Lead].ability = Ability_List[ability_str]

                # terrain/room end
                elif (line[1].startswith("-fieldend")):
                    field_str = line[2].replace("move:", "").strip()
                    if field_str.startswith("Trick"):
                        self.rickRoom = False
                    elif field_str.startswith("Wonder"):
                        self.wonderRoom = False
                    elif field_str.startswith("Gravity"):
                        self.gravity = True
                    elif field_str.endswith("Terrain"):
                        self.terrain = Terrain_List.NoTerrain
                    elif field_str.startswith("Magic"):
                        self.magicRoom = True
                    else: # error?
                        print("Unknown field start:", line)
                        exit()

                # this is where stealth rock and other one side events happen
                elif (line[1].startswith("-sidestart")):
                    if (line[2][1] == '1'):
                        hazard = Hazards_List[line[3].replace(" ", "").replace("move:", "")]
                        if ((hazard == Hazards_List.ToxicSpikes) and (self.p1Hazards & Hazards_List.ToxicSpikes)):
                            hazard = Hazards_List.ToxicSpikes2

                        elif ((hazard == Hazards_List.Spikes) and (self.p1Hazards & Hazards_List.Spikes)):

                            if ((hazard == Hazards_List.Spikes) and (self.p1Hazards & Hazards_List.Spikes2)):
                                hazard = Hazards_List.Spikes3
                            else:
                                hazard = Hazards_List.Spikes2

                        self.p1Hazards &= hazard
                    else:
                        hazard = Hazards_List[line[3].replace(" ", "").replace("move:", "")]
                        if ((hazard == Hazards_List.ToxicSpikes) and (self.p1Hazards & Hazards_List.ToxicSpikes)):
                            hazard = Hazards_List.ToxicSpikes2
                        elif ((hazard == Hazards_List.Spikes) and (self.p1Hazards & Hazards_List.Spikes)):

                            if ((hazard == Hazards_List.Spikes) and (self.p1Hazards & Hazards_List.Spikes2)):
                                hazard = Hazards_List.Spikes3
                            else:
                                hazard = Hazards_List.Spikes2

                        self.p2Hazards &= hazard

                # inverse side start, idk where this will appear
                # besides defog
                elif (line[1].startswith("-sideend")):
                    if (line[2][1] == '1'):
                        self.p1Hazards ^= ~Hazards_List[line[3].replace(" ", "").replace("move:", "")]
                    else:
                        self.p2Hazards ^= ~Hazards_List[line[3].replace(" ", "").replace("move:", "")]

                # volatile status (confusion, taunt, sub)
                elif (line[1].startswith("-start")):
                    if (line[2][1] == '1'):
                        
                        if (line[3] == "typechange"):
                            if (len(line) > 5):
                                if ("Burn Up" in line[5]):
                                    types = line[4].split("\\/")
                                    tempType = []
                                    for x in types:
                                        tempType.append(Types[x.replace("???", "question").lower()])
                                    self.p1Party[self.p1Lead].OverrideType = tempType
                                else:
                                    self.p1Party[self.p1Lead].OverrideType = [Types[line[4].lower()]]
                        self.p1Volatile &= Volatile_List[line[3].replace(" ", "").replace("move:", "").replace("ability:", "")]
                    else:
                        if (line[3] == "typechange"):
                            if (len(line) > 5):
                                if ("Burn Up" in line[5]):
                                    types = line[4].split("\\/")
                                    tempType = []
                                    for x in types:
                                        tempType.append(Types[x.replace("???", "question").lower()])
                                    self.p2Party[self.p2Lead].OverrideType = tempType
                                else:
                                    self.p2Party[self.p2Lead].OverrideType = [Types[line[4].lower()]]

                # inverse volatile status (confusion, taunt, sub)
                elif (line[1] == "-end"):
                    if (line[2][1] == '1'):
                        if (line[3] == "typechange"):
                            self.p1Party[self.p1Lead].OverrideType = [Type.NoType]
                        self.p1Volatile &= ~Volatile_List[line[3].replace(" ", "").replace("move:", "").replace("ability:", "")]
                    else:
                        if (line[3] == "typechange"):
                            self.p1Party[self.p1Lead].OverrideType = [Type.NoType]
                        self.p2Volatile &= ~Volatile_List[line[3].replace(" ", "").replace("move:", "").replace("ability:", "")]

                # it always mattered
                elif (line[1].startswith("-crit")):
                    if (line[2][1] == '1'):
                        self.p1Crit = True
                    else:
                        self.p2Crit = True

                # yes
                # idt this matters since the numbers would be bigger anyways
                elif (line[1].startswith("-supereffective")):
                    pass

                # no
                # idt this matters since the numbers would be smaller anyways
                elif (line[1].startswith("-resisted")):
                    pass

                # NO
                # idt this matters since the numbers would be 0 anyways
                elif (line[1].startswith("-immune")):
                    pass

                # leftovers/life orb reveal
                elif (line[1].startswith("-item")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].item = line[3].replace(" ", "")
                    else:
                        self.p2Party[self.p2Lead].item = line[3].replace(" ", "")

                # knock off
                elif (line[1].startswith("-enditem")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].item = "None"
                    else:
                        self.p2Party[self.p2Lead].item = "None"

                # set the ability on a pokemon
                # and maybe also handle intimidate and stuff
                elif (line[1].startswith("-ability")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].Ability = Ability_List[line[3].replace(" ", "").replace("-","")]
                    else:
                        self.p2Party[self.p2Lead].Ability = Ability_List[line[3].replace(" ", "").replace("-","")]

                # suppressed by gastro acid
                # idk how to even approach this
                elif (line[1].startswith("-endability")):
                    pass

                # ditto is cool
                # clear the moves on transform so stuff does not break?
                # or maybe instead we just copy your own moves?
                elif (line[1].startswith("-transform")):
                    if (line[2][1] == '1'):
                        self.p1Party[self.p1Lead].Transformed = True
                    else:
                        self.p2Party[self.p2Lead].Transformed = True

                # unused in gen 8
                elif (line[1].startswith("-primal")):
                    pass

                # unused in gen 8?
                elif (line[1].startswith("-burst")):
                    pass

                # unused in gen 8?
                elif (line[1].startswith("-zpower")):
                    pass

                # unused in gen 8?
                elif (line[1].startswith("-zbroken")):
                    pass

                # basically useless info?
                elif (line[1].startswith("-activate")):
                    pass

                # basically useless info?
                elif (line[1].startswith("-hint")):
                    pass

                # basically useless info?
                elif (line[1].startswith("-center")):
                    pass

                # other messages for stuff like rules, useless
                elif (line[1].startswith("-message")):
                    pass

                # useless in singles
                elif (line[1].startswith("-combine")):
                    pass

                # useless in singles
                elif (line[1].startswith("-waiting")):
                    pass

                # charge moves, I hope this is useless
                elif (line[1].startswith("-prepare")):
                    pass

                # charge moves, I hope this is useless
                elif (line[1].startswith("-mustrecharge")):
                    pass

                # splash
                elif (line[1].startswith("-nothing")):
                    pass

                # the definition for this is that it updates turn timers
                # idk if we want to worry about that
                elif (line[1].startswith("upkeep")):
                    pass

                # cloyster go brrr
                elif (line[1].startswith("-hitcount")):
                    pass

                # d-bond
                elif (line[1].startswith("-singlemove")):
                    pass

                # protect, focus punch, roost
                elif (line[1].startswith("-singleturn")):
                    pass

                # timestamp
                elif (line[1].startswith("t:")):
                    pass

                # idek, blanks appear
                elif (line[1].startswith("")):
                    pass

                else:
                    print("Error, unknown instruction:", line[1])
                    exit()

                    
                line = fp.readline().strip()
                while ((line == "|") or (line == "") or (line[0] != "|")):
                    line = fp.readline().strip()
                # print(line)
                line = line.split("|")
            
            return

    # currently unused
    def predictSpeed(self): # if this returns true, speed is currently "accurate"
        #return self.p1Party[self.p1Lead].
        return True

    def GetVector(self):
        theMonster = [] # this should contain the party and anything else that might be useful
        output = [] # this should contain the moves and switches people clicked
        for x in self.p1Party:
            vec = x.GetVector()
            for y in vec:
                theMonster.append(y)
        
        for x in self.p2Party:
            vec = x.GetVector()
            for y in vec:
                theMonster.append(y)

        theMonster.append(int(self.terrain))
        theMonster.append(int(self.weather))
        # encode trick/wonder room as true = 1, false = -1
        if (self.trickRoom):
            theMonster.append(1)
        else:
            theMonster.append(-1)
        if (self.wonderRoom):
            theMonster.append(1)
        else:
            theMonster.append(-1)
        if (self.magicRoom):
            theMonster.append(1)
        else:
            theMonster.append(-1)

        theMonster.append(self.p1Lead)
        if (self.p1Party[self.p1Lead].Transformed):
            theMonster.append(1)
        else:
            theMonster.append(-1)
        theMonster.append(int(self.p1Hazards))
        theMonster.append(int(self.p1Volatile))
        for x in self.p1Boosts:
            theMonster.append(x)
        
        theMonster.append(self.p2Lead)
        if (self.p2Party[self.p2Lead].Transformed):
            theMonster.append(1)
        else:
            theMonster.append(-1)
        theMonster.append(int(self.p2Hazards))
        theMonster.append(int(self.p2Volatile))
        for x in self.p2Boosts:
            theMonster.append(x)

        # we also want the current field/terrains
        if (self.isTurn0):
            # at team preview, get teams for each side starting with 
            # the player
            # the output is no move for each side, and the lead as a switch
            output.append(5)
            output.append(5)
            output.append(0)
            output.append(0)
        else:
            output.append(self.p1Move)
            output.append(self.p2Move)
            # if not then we use the current pokemon as the other inputs?
            output.append(self.p1Switch)
            output.append(self.p2Switch)
            
            # and the output is still moves and potential switches
        return theMonster, output

    def GenerateFiles(self, inputCsv, outputCsv):
        input, output = self.GetVector()
        with open(inputCsv, "a") as fpw:
            fpw.write(str(input[0]))
            for x in input[1:]:
                fpw.write("," + str(x))
            fpw.write("\n")
        with open(outputCsv, "a") as fpw:
            fpw.write(str(output[0]))
            for x in output[1:]:
                fpw.write("," + str(x))
            fpw.write("\n")
        return
    # going to try to follow the PS turn style
    # this is extremely inaccurate right now
    # def __str__(self):
    #     if (self.isTurn0):
    #         string = "Start\nP{} sends out: ".format(self.first)
    #         # this logic probably matters
    #         if (self.first == 1):
    #             string += self.p1Lead + "\nP2 sends out: " + self.p2Lead
    #         else:
    #             string += self.p2Lead + "\nP1 sends out: " + self.p1Lead
    # 
    #         if (len(self.fields) > 1):
    #             for x in self.fields[1:]:
    #                 string += "\n" + str(x) + "\n" # this part does not print properly but it's too much work
    #         string += "End of turn 0"
    #     else:
    #         pass
    # 
    #     return string


####################################################################################
# defines a single pokemon                                                         #
# data stored includes:                                                            #
# the pokemon itself as a pypokedex object: for accessing the dex number           #
# known and unknown moves as well as used PP: traditionally this affects decisions #
# on what switch ins to make, and unknown moves are powerful                       #
# ability,gender and item: influence what sets are being run and decisions         #
####################################################################################
class Pokemon():
    # initalizer for known pokemon
    def __init__(self, poke="Porygon", gender=0):
        poke = poke.replace(" ", "-").replace(".", "")
        
        # fsr these always keep the wrong string through a replay
        # the rest are non standard forms that pop up
        if (poke == "Darmanitan"):
            poke = "Darmanitan-standard"
        elif(poke == "Toxtricity"): 
            poke = "Toxtricity-amped"
        elif (poke == "Mimikyu"):
            poke = "Mimikyu-disguised"
        elif (poke == "Basculin"):
            poke = "Basculin-red-striped"
        elif (poke == "Eiscue"):
            poke = "Eiscue-ice"
        elif (poke == "Indeedee-F"):
            poke = "Indeedee-Female"
        elif (poke == "Indeedee-M"):
            poke = "Indeedee-Male"
        elif (poke == "Aegislash"):
            poke = "Aegislash-shield"
        elif (poke == "Farfetch\\u2019d"):
            poke = "Farfetchd"
        elif (poke == "Sirfetch\\u2019d"):
            poke = "Sirfetchd"
        elif (poke == "Gastrodon-East"):
            poke = "Gastrodon"
        elif (poke == "Gastrodon-West"):
            poke = "Gastrodon"
        elif (poke == "Thundurus"):
            poke = "Thundurus-Incarnate"
        elif (poke == "Landorus"):
            poke = "Landorus-Incarnate"
        elif (poke == "Tornadus"):
            poke = "Tornadus-Incarnate"
        elif (poke == "Zygarde-10%"):
            poke = "Zygarde-10"
        elif (poke.startswith("Meowstic")):
            if (gender == Gender.M):
                if poke.endswith("-M"):
                    poke += "ale"
                else:
                    poke += "-Male"
            else:
                if poke.endswith("-F"):
                    poke += "emale"
                else:
                    poke += "-Female"
        elif (poke == "Indeedee"):
            if (gender == Gender.M):
                poke += "-Male"
            else:
                poke += "-Female"
        elif (poke == "Polteageist-Antique"):
            poke = "Polteageist"
        elif (poke == "Zarude-Dada"):
            poke = "Zarude"
        elif (poke == "Keldeo"):
            poke = "Keldeo-ordinary"
        elif (poke == "Lycanroc"):
            poke = "Lycanroc-Midday"
        elif (poke.startswith("Pikachu")):
            poke = "Pikachu"
        try:
            self.Pkmn = pkd.get(name=poke)
        except:
            print("Unknown pokemon:", poke)
        self.Moves = [Move_List.Unknown, Move_List.Unknown, Move_List.Unknown, Move_List.Unknown]
        self.FilledMoves = 0
        self.PP = [0, 0, 0, 0]
        theTypes = self.Pkmn.types
        self.Type = [Types.NoType, Types.NoType]
        for x in range(len(theTypes)):
            self.Type[x] = Types[theTypes[x]]
        self.OverrideType = [Types.NoType]
        self.Ability = Ability_List.Unknown
        self.Item = ""
        self.Gender = gender
        self.Level = 100 # this should be changed at some point
        self.Speed = self.calcSpeed()
        self.HP = 100
        self.Status = Status_List.non
        self.Transformed = False
        self.TransformMoves = [Move_List.Unknown, Move_List.Unknown, Move_List.Unknown, Move_List.Unknown]
        self.TransformFilled = 0
        self.TransformPP = [0, 0, 0, 0]
        
    def calcSpeed(self): # this will assume neutral speed 0 ev investment
        return ((2 * self.Pkmn.base_stats[5] + 31) * self.Level) / 100 + 5
        
    def GetVector(self):
        self.stats = self.Pkmn.base_stats
        vec = [
        self.stats[0], self.stats[1], self.stats[2], # HP,  Atk, Def
        self.stats[3], self.stats[4], self.stats[5], # SpA, SpD, Spe
        int(self.Moves[0]), self.PP[0],                   # move 1
        int(self.Moves[1]), self.PP[1],                   # move 2
        int(self.Moves[2]), self.PP[2],                   # move 3
        int(self.Moves[3]), self.PP[3],                   # move 4
        int(self.Ability)] # anything else should be appended here
        if (self.Transformed):
            vec.append(1)
        else:
            vec.append(-1)
        return vec

    def AddMove(self, move):
        # first check if transform is active or used
        if (self.Transformed):
            try:
                ind = self.TransformMoves.index(move)
            except:
                self.TransformMoves[self.TransformFilled] = move
                ind = self.FilledMoves
            self.TransformPP[ind] += 1
            return
        elif (move == Move_List.Transform):
            self.Transformed = True
        # then check if the move exists
        try:
            ind = self.Moves.index(move)
        except:
            self.Moves[self.FilledMoves] = move
            ind = self.FilledMoves
            self.FilledMoves += 1
        self.PP[ind] += 1
        return
    # this is a hack to solve ditto overflowing moves
    def ResetMoves(self):
        self.Moves = [Move_List.Unknown, Move_List.Unknown, Move_List.Unknown, Move_List.Unknown]
        self.FilledMoves = 0
        
    def ResetTransformMoves(self):
        self.TransformMoves = [Move_List.Unknown, Move_List.Unknown, Move_List.Unknown, Move_List.Unknown]
        self.FilledMoves = 0

    # Tries to follow the showdown format because why not, some things are changed for readability
    def __str__(self):
        string = self.Pkmn.name
        if (self.Item):
            string += "@ " + self.Item
        string += "\nAbility: " + str(self.Ability) + "\n"
        # string += "EVs:" # this would not work unless we galaxy brain predict them somehow
        # string += Nature + " Nature" # above
        
        if (self.Moves[0] == Move_List.Unknown):
            string += "No known moves"
        elif (self.Transformed):
            string += "- " + self.TransformMoves[0].name + "\n" + \
                      "- " + self.TransformMoves[1].name + "\n" + \
                      "- " + self.TransformMoves[2].name + "\n" + \
                      "- " + self.TransformMoves[3].name + "\n"
        else:
            string += "- " + self.Moves[0].name + "(" + str(self.PP[0]) + ")\n" + \
                      "- " + self.Moves[1].name + "(" + str(self.PP[1]) + ")\n" + \
                      "- " + self.Moves[2].name + "(" + str(self.PP[2]) + ")\n" + \
                      "- " + self.Moves[3].name + "(" + str(self.PP[3]) + ")\n"
        return string

# Gender is something that PS keeps track of so we might as well have it
class Gender(IntEnum):
    G = 0
    M = 1
    F = 2

# Volatile status are things that can get cleared over time or on switch
class Volatile_List(IntFlag):
    NoVolatile = 0
    bind = auto()
    block = auto()
    confusion = auto()
    substitute = auto()
    MagmaStorm = auto()
    LeechSeed = auto()
    Taunt = auto()
    StickyBarb = auto()
    Substitute = auto()
    FutureSight = auto()
    ThroatChop = auto()
    Yawn = auto()
    Disable = auto()
    FocusEnergy = auto()
    FlashFire = auto()
    ThunderCage = auto()
    Wrap = auto()
    Encore = auto()
    Autotomize = auto()
    Curse = auto()
    Illusion = auto() # probably drop this because I dropped zoroark
    perish3 = auto()
    perish2 = auto()
    perish1 = auto()
    perish0 = auto()
    SandTomb = auto()
    Whirlpool = auto()
    NeutralizingGas = auto()
    typechange = auto()
    Infestation = auto()
    Octolock = auto()
    NoRetreat = auto()
    SmackDown = auto()
    Torment = auto()
    Attract = auto()
    DoomDesire = auto()
    stockpile1 = auto()
    stockpile2 = auto()
    stockpile3 = auto()
    AquaRing = auto()
    SlowStart = auto()
    SnapTrap = auto()
    MagnetRise = auto()
    FireSpin = auto()
    Imprison = auto()
    PowerTrick = auto()

class Stat_List(IntEnum):
    atkS = 0
    defS = 1
    spaS = 2
    spdS = 3
    speS = 4
    evasionS = 5
    accuracyS = 6
    
class Types(IntEnum):
    NoType = 0
    normal = 1
    fighting = 2
    flying = 3
    poison = 4
    ground = 5
    rock = 6
    bug = 7
    ghost = 8
    steel = 9
    fire = 10
    water = 11
    grass = 12
    electric = 13
    psychic = 14
    ice = 15
    dragon = 16
    dark = 17
    fairy = 18
    question = 19
    

####################################################################################
# Move and ability lists derived from here because they are sorted                 #
# https://github.com/kwsch/PKHeX/blob/master/PKHeX.Core/Game/Enums/                #
# this order was derived from data mining the video games and has not changed      #
# since gen 1                                                                      #
####################################################################################
class Move_List(IntEnum):
    Unknown = 0 # the only change because None is a keyword
    Pound = auto()
    KarateChop = auto()
    DoubleSlap = auto()
    CometPunch = auto()
    MegaPunch = auto()
    PayDay = auto()
    FirePunch = auto()
    IcePunch = auto()
    ThunderPunch = auto()
    Scratch = auto()
    ViseGrip = auto()
    Guillotine = auto()
    RazorWind = auto()
    SwordsDance = auto()
    Cut = auto()
    Gust = auto()
    WingAttack = auto()
    Whirlwind = auto()
    Fly = auto()
    Bind = auto()
    Slam = auto()
    VineWhip = auto()
    Stomp = auto()
    DoubleKick = auto()
    MegaKick = auto()
    JumpKick = auto()
    RollingKick = auto()
    SandAttack = auto()
    Headbutt = auto()
    HornAttack = auto()
    FuryAttack = auto()
    HornDrill = auto()
    Tackle = auto()
    BodySlam = auto()
    Wrap = auto()
    TakeDown = auto()
    Thrash = auto()
    DoubleEdge = auto()
    TailWhip = auto()
    PoisonSting = auto()
    Twineedle = auto()
    PinMissile = auto()
    Leer = auto()
    Bite = auto()
    Growl = auto()
    Roar = auto()
    Sing = auto()
    Supersonic = auto()
    SonicBoom = auto()
    Disable = auto()
    Acid = auto()
    Ember = auto()
    Flamethrower = auto()
    Mist = auto()
    WaterGun = auto()
    HydroPump = auto()
    Surf = auto()
    IceBeam = auto()
    Blizzard = auto()
    Psybeam = auto()
    BubbleBeam = auto()
    AuroraBeam = auto()
    HyperBeam = auto()
    Peck = auto()
    DrillPeck = auto()
    Submission = auto()
    LowKick = auto()
    Counter = auto()
    SeismicToss = auto()
    Strength = auto()
    Absorb = auto()
    MegaDrain = auto()
    LeechSeed = auto()
    Growth = auto()
    RazorLeaf = auto()
    SolarBeam = auto()
    PoisonPowder = auto()
    StunSpore = auto()
    SleepPowder = auto()
    PetalDance = auto()
    StringShot = auto()
    DragonRage = auto()
    FireSpin = auto()
    ThunderShock = auto()
    Thunderbolt = auto()
    ThunderWave = auto()
    Thunder = auto()
    RockThrow = auto()
    Earthquake = auto()
    Fissure = auto()
    Dig = auto()
    Toxic = auto()
    Confusion = auto()
    Psychic = auto()
    Hypnosis = auto()
    Meditate = auto()
    Agility = auto()
    QuickAttack = auto()
    Rage = auto()
    Teleport = auto()
    NightShade = auto()
    Mimic = auto()
    Screech = auto()
    DoubleTeam = auto()
    Recover = auto()
    Harden = auto()
    Minimize = auto()
    Smokescreen = auto()
    ConfuseRay = auto()
    Withdraw = auto()
    DefenseCurl = auto()
    Barrier = auto()
    LightScreen = auto()
    Haze = auto()
    Reflect = auto()
    FocusEnergy = auto()
    Bide = auto()
    Metronome = auto()
    MirrorMove = auto()
    SelfDestruct = auto()
    EggBomb = auto()
    Lick = auto()
    Smog = auto()
    Sludge = auto()
    BoneClub = auto()
    FireBlast = auto()
    Waterfall = auto()
    Clamp = auto()
    Swift = auto()
    SkullBash = auto()
    SpikeCannon = auto()
    Constrict = auto()
    Amnesia = auto()
    Kinesis = auto()
    SoftBoiled = auto()
    HighJumpKick = auto()
    Glare = auto()
    DreamEater = auto()
    PoisonGas = auto()
    Barrage = auto()
    LeechLife = auto()
    LovelyKiss = auto()
    SkyAttack = auto()
    Transform = auto()
    Bubble = auto()
    DizzyPunch = auto()
    Spore = auto()
    Flash = auto()
    Psywave = auto()
    Splash = auto()
    AcidArmor = auto()
    Crabhammer = auto()
    Explosion = auto()
    FurySwipes = auto()
    Bonemerang = auto()
    Rest = auto()
    RockSlide = auto()
    HyperFang = auto()
    Sharpen = auto()
    Conversion = auto()
    TriAttack = auto()
    SuperFang = auto()
    Slash = auto()
    Substitute = auto()
    Struggle = auto()
    Sketch = auto()
    TripleKick = auto()
    Thief = auto()
    SpiderWeb = auto()
    MindReader = auto()
    Nightmare = auto()
    FlameWheel = auto()
    Snore = auto()
    Curse = auto()
    Flail = auto()
    Conversion2 = auto()
    Aeroblast = auto()
    CottonSpore = auto()
    Reversal = auto()
    Spite = auto()
    PowderSnow = auto()
    Protect = auto()
    MachPunch = auto()
    ScaryFace = auto()
    FeintAttack = auto()
    SweetKiss = auto()
    BellyDrum = auto()
    SludgeBomb = auto()
    MudSlap = auto()
    Octazooka = auto()
    Spikes = auto()
    ZapCannon = auto()
    Foresight = auto()
    DestinyBond = auto()
    PerishSong = auto()
    IcyWind = auto()
    Detect = auto()
    BoneRush = auto()
    LockOn = auto()
    Outrage = auto()
    Sandstorm = auto()
    GigaDrain = auto()
    Endure = auto()
    Charm = auto()
    Rollout = auto()
    FalseSwipe = auto()
    Swagger = auto()
    MilkDrink = auto()
    Spark = auto()
    FuryCutter = auto()
    SteelWing = auto()
    MeanLook = auto()
    Attract = auto()
    SleepTalk = auto()
    HealBell = auto()
    Return = auto()
    Present = auto()
    Frustration = auto()
    Safeguard = auto()
    PainSplit = auto()
    SacredFire = auto()
    Magnitude = auto()
    DynamicPunch = auto()
    Megahorn = auto()
    DragonBreath = auto()
    BatonPass = auto()
    Encore = auto()
    Pursuit = auto()
    RapidSpin = auto()
    SweetScent = auto()
    IronTail = auto()
    MetalClaw = auto()
    VitalThrow = auto()
    MorningSun = auto()
    Synthesis = auto()
    Moonlight = auto()
    HiddenPower = auto()
    CrossChop = auto()
    Twister = auto()
    RainDance = auto()
    SunnyDay = auto()
    Crunch = auto()
    MirrorCoat = auto()
    PsychUp = auto()
    ExtremeSpeed = auto()
    AncientPower = auto()
    ShadowBall = auto()
    FutureSight = auto()
    RockSmash = auto()
    Whirlpool = auto()
    BeatUp = auto()
    FakeOut = auto()
    Uproar = auto()
    Stockpile = auto()
    SpitUp = auto()
    Swallow = auto()
    HeatWave = auto()
    Hail = auto()
    Torment = auto()
    Flatter = auto()
    WillOWisp = auto()
    Memento = auto()
    Facade = auto()
    FocusPunch = auto()
    SmellingSalts = auto()
    FollowMe = auto()
    NaturePower = auto()
    Charge = auto()
    Taunt = auto()
    HelpingHand = auto()
    Trick = auto()
    RolePlay = auto()
    Wish = auto()
    Assist = auto()
    Ingrain = auto()
    Superpower = auto()
    MagicCoat = auto()
    Recycle = auto()
    Revenge = auto()
    BrickBreak = auto()
    Yawn = auto()
    KnockOff = auto()
    Endeavor = auto()
    Eruption = auto()
    SkillSwap = auto()
    Imprison = auto()
    Refresh = auto()
    Grudge = auto()
    Snatch = auto()
    SecretPower = auto()
    Dive = auto()
    ArmThrust = auto()
    Camouflage = auto()
    TailGlow = auto()
    LusterPurge = auto()
    MistBall = auto()
    FeatherDance = auto()
    TeeterDance = auto()
    BlazeKick = auto()
    MudSport = auto()
    IceBall = auto()
    NeedleArm = auto()
    SlackOff = auto()
    HyperVoice = auto()
    PoisonFang = auto()
    CrushClaw = auto()
    BlastBurn = auto()
    HydroCannon = auto()
    MeteorMash = auto()
    Astonish = auto()
    WeatherBall = auto()
    Aromatherapy = auto()
    FakeTears = auto()
    AirCutter = auto()
    Overheat = auto()
    OdorSleuth = auto()
    RockTomb = auto()
    SilverWind = auto()
    MetalSound = auto()
    GrassWhistle = auto()
    Tickle = auto()
    CosmicPower = auto()
    WaterSpout = auto()
    SignalBeam = auto()
    ShadowPunch = auto()
    Extrasensory = auto()
    SkyUppercut = auto()
    SandTomb = auto()
    SheerCold = auto()
    MuddyWater = auto()
    BulletSeed = auto()
    AerialAce = auto()
    IcicleSpear = auto()
    IronDefense = auto()
    Block = auto()
    Howl = auto()
    DragonClaw = auto()
    FrenzyPlant = auto()
    BulkUp = auto()
    Bounce = auto()
    MudShot = auto()
    PoisonTail = auto()
    Covet = auto()
    VoltTackle = auto()
    MagicalLeaf = auto()
    WaterSport = auto()
    CalmMind = auto()
    LeafBlade = auto()
    DragonDance = auto()
    RockBlast = auto()
    ShockWave = auto()
    WaterPulse = auto()
    DoomDesire = auto()
    PsychoBoost = auto()
    Roost = auto()
    Gravity = auto()
    MiracleEye = auto()
    WakeUpSlap = auto()
    HammerArm = auto()
    GyroBall = auto()
    HealingWish = auto()
    Brine = auto()
    NaturalGift = auto()
    Feint = auto()
    Pluck = auto()
    Tailwind = auto()
    Acupressure = auto()
    MetalBurst = auto()
    Uturn = auto()
    CloseCombat = auto()
    Payback = auto()
    Assurance = auto()
    Embargo = auto()
    Fling = auto()
    PsychoShift = auto()
    TrumpCard = auto()
    HealBlock = auto()
    WringOut = auto()
    PowerTrick = auto()
    GastroAcid = auto()
    LuckyChant = auto()
    MeFirst = auto()
    Copycat = auto()
    PowerSwap = auto()
    GuardSwap = auto()
    Punishment = auto()
    LastResort = auto()
    WorrySeed = auto()
    SuckerPunch = auto()
    ToxicSpikes = auto()
    HeartSwap = auto()
    AquaRing = auto()
    MagnetRise = auto()
    FlareBlitz = auto()
    ForcePalm = auto()
    AuraSphere = auto()
    RockPolish = auto()
    PoisonJab = auto()
    DarkPulse = auto()
    NightSlash = auto()
    AquaTail = auto()
    SeedBomb = auto()
    AirSlash = auto()
    XScissor = auto()
    BugBuzz = auto()
    DragonPulse = auto()
    DragonRush = auto()
    PowerGem = auto()
    DrainPunch = auto()
    VacuumWave = auto()
    FocusBlast = auto()
    EnergyBall = auto()
    BraveBird = auto()
    EarthPower = auto()
    Switcheroo = auto()
    GigaImpact = auto()
    NastyPlot = auto()
    BulletPunch = auto()
    Avalanche = auto()
    IceShard = auto()
    ShadowClaw = auto()
    ThunderFang = auto()
    IceFang = auto()
    FireFang = auto()
    ShadowSneak = auto()
    MudBomb = auto()
    PsychoCut = auto()
    ZenHeadbutt = auto()
    MirrorShot = auto()
    FlashCannon = auto()
    RockClimb = auto()
    Defog = auto()
    TrickRoom = auto()
    DracoMeteor = auto()
    Discharge = auto()
    LavaPlume = auto()
    LeafStorm = auto()
    PowerWhip = auto()
    RockWrecker = auto()
    CrossPoison = auto()
    GunkShot = auto()
    IronHead = auto()
    MagnetBomb = auto()
    StoneEdge = auto()
    Captivate = auto()
    StealthRock = auto()
    GrassKnot = auto()
    Chatter = auto()
    Judgment = auto()
    BugBite = auto()
    ChargeBeam = auto()
    WoodHammer = auto()
    AquaJet = auto()
    AttackOrder = auto()
    DefendOrder = auto()
    HealOrder = auto()
    HeadSmash = auto()
    DoubleHit = auto()
    RoarofTime = auto()
    SpacialRend = auto()
    LunarDance = auto()
    CrushGrip = auto()
    MagmaStorm = auto()
    DarkVoid = auto()
    SeedFlare = auto()
    OminousWind = auto()
    ShadowForce = auto()
    HoneClaws = auto()
    WideGuard = auto()
    GuardSplit = auto()
    PowerSplit = auto()
    WonderRoom = auto()
    Psyshock = auto()
    Venoshock = auto()
    Autotomize = auto()
    RagePowder = auto()
    Telekinesis = auto()
    MagicRoom = auto()
    SmackDown = auto()
    StormThrow = auto()
    FlameBurst = auto()
    SludgeWave = auto()
    QuiverDance = auto()
    HeavySlam = auto()
    Synchronoise = auto()
    ElectroBall = auto()
    Soak = auto()
    FlameCharge = auto()
    Coil = auto()
    LowSweep = auto()
    AcidSpray = auto()
    FoulPlay = auto()
    SimpleBeam = auto()
    Entrainment = auto()
    AfterYou = auto()
    Round = auto()
    EchoedVoice = auto()
    ChipAway = auto()
    ClearSmog = auto()
    StoredPower = auto()
    QuickGuard = auto()
    AllySwitch = auto()
    Scald = auto()
    ShellSmash = auto()
    HealPulse = auto()
    Hex = auto()
    SkyDrop = auto()
    ShiftGear = auto()
    CircleThrow = auto()
    Incinerate = auto()
    Quash = auto()
    Acrobatics = auto()
    ReflectType = auto()
    Retaliate = auto()
    FinalGambit = auto()
    Bestow = auto()
    Inferno = auto()
    WaterPledge = auto()
    FirePledge = auto()
    GrassPledge = auto()
    VoltSwitch = auto()
    StruggleBug = auto()
    Bulldoze = auto()
    FrostBreath = auto()
    DragonTail = auto()
    WorkUp = auto()
    Electroweb = auto()
    WildCharge = auto()
    DrillRun = auto()
    DualChop = auto()
    HeartStamp = auto()
    HornLeech = auto()
    SacredSword = auto()
    RazorShell = auto()
    HeatCrash = auto()
    LeafTornado = auto()
    Steamroller = auto()
    CottonGuard = auto()
    NightDaze = auto()
    Psystrike = auto()
    TailSlap = auto()
    Hurricane = auto()
    HeadCharge = auto()
    GearGrind = auto()
    SearingShot = auto()
    TechnoBlast = auto()
    RelicSong = auto()
    SecretSword = auto()
    Glaciate = auto()
    BoltStrike = auto()
    BlueFlare = auto()
    FieryDance = auto()
    FreezeShock = auto()
    IceBurn = auto()
    Snarl = auto()
    IcicleCrash = auto()
    Vcreate = auto()
    FusionFlare = auto()
    FusionBolt = auto()
    FlyingPress = auto()
    MatBlock = auto()
    Belch = auto()
    Rototiller = auto()
    StickyWeb = auto()
    FellStinger = auto()
    PhantomForce = auto()
    TrickorTreat = auto()
    NobleRoar = auto()
    IonDeluge = auto()
    ParabolicCharge = auto()
    ForestsCurse = auto()
    PetalBlizzard = auto()
    FreezeDry = auto()
    DisarmingVoice = auto()
    PartingShot = auto()
    TopsyTurvy = auto()
    DrainingKiss = auto()
    CraftyShield = auto()
    FlowerShield = auto()
    GrassyTerrain = auto()
    MistyTerrain = auto()
    Electrify = auto()
    PlayRough = auto()
    FairyWind = auto()
    Moonblast = auto()
    Boomburst = auto()
    FairyLock = auto()
    KingsShield = auto()
    PlayNice = auto()
    Confide = auto()
    DiamondStorm = auto()
    SteamEruption = auto()
    HyperspaceHole = auto()
    WaterShuriken = auto()
    MysticalFire = auto()
    SpikyShield = auto()
    AromaticMist = auto()
    EerieImpulse = auto()
    VenomDrench = auto()
    Powder = auto()
    Geomancy = auto()
    MagneticFlux = auto()
    HappyHour = auto()
    ElectricTerrain = auto()
    DazzlingGleam = auto()
    Celebrate = auto()
    HoldHands = auto()
    BabyDollEyes = auto()
    Nuzzle = auto()
    HoldBack = auto()
    Infestation = auto()
    PowerUpPunch = auto()
    OblivionWing = auto()
    ThousandArrows = auto()
    ThousandWaves = auto()
    LandsWrath = auto()
    LightofRuin = auto()
    OriginPulse = auto()
    PrecipiceBlades = auto()
    DragonAscent = auto()
    HyperspaceFury = auto()
    BreakneckBlitzP = auto()
    BreakneckBlitzS = auto()
    AllOutPummelingP = auto()
    AllOutPummelingS = auto()
    SupersonicSkystrikeP = auto()
    SupersonicSkystrikeS = auto()
    AcidDownpourP = auto()
    AcidDownpourS = auto()
    TectonicRageP = auto()
    TectonicRageS = auto()
    ContinentalCrushP = auto()
    ContinentalCrushS = auto()
    SavageSpinOutP = auto()
    SavageSpinOutS = auto()
    NeverEndingNightmareP = auto()
    NeverEndingNightmareS = auto()
    CorkscrewCrashP = auto()
    CorkscrewCrashS = auto()
    InfernoOverdriveP = auto()
    InfernoOverdriveS = auto()
    HydroVortexP = auto()
    HydroVortexS = auto()
    BloomDoomP = auto()
    BloomDoomS = auto()
    GigavoltHavocP = auto()
    GigavoltHavocS = auto()
    ShatteredPsycheP = auto()
    ShatteredPsycheS = auto()
    SubzeroSlammerP = auto()
    SubzeroSlammerS = auto()
    DevastatingDrakeP = auto()
    DevastatingDrakeS = auto()
    BlackHoleEclipseP = auto()
    BlackHoleEclipseS = auto()
    TwinkleTackleP = auto()
    TwinkleTackleS = auto()
    Catastropika = auto()
    ShoreUp = auto()
    FirstImpression = auto()
    BanefulBunker = auto()
    SpiritShackle = auto()
    DarkestLariat = auto()
    SparklingAria = auto()
    IceHammer = auto()
    FloralHealing = auto()
    HighHorsepower = auto()
    StrengthSap = auto()
    SolarBlade = auto()
    Leafage = auto()
    Spotlight = auto()
    ToxicThread = auto()
    LaserFocus = auto()
    GearUp = auto()
    ThroatChop = auto()
    PollenPuff = auto()
    AnchorShot = auto()
    PsychicTerrain = auto()
    Lunge = auto()
    FireLash = auto()
    PowerTrip = auto()
    BurnUp = auto()
    SpeedSwap = auto()
    SmartStrike = auto()
    Purify = auto()
    RevelationDance = auto()
    CoreEnforcer = auto()
    TropKick = auto()
    Instruct = auto()
    BeakBlast = auto()
    ClangingScales = auto()
    DragonHammer = auto()
    BrutalSwing = auto()
    AuroraVeil = auto()
    SinisterArrowRaid = auto()
    MaliciousMoonsault = auto()
    OceanicOperetta = auto()
    GuardianofAlola = auto()
    SoulStealing7StarStrike = auto()
    StokedSparksurfer = auto()
    PulverizingPancake = auto()
    ExtremeEvoboost = auto()
    GenesisSupernova = auto()
    ShellTrap = auto()
    FleurCannon = auto()
    PsychicFangs = auto()
    StompingTantrum = auto()
    ShadowBone = auto()
    Accelerock = auto()
    Liquidation = auto()
    PrismaticLaser = auto()
    SpectralThief = auto()
    SunsteelStrike = auto()
    MoongeistBeam = auto()
    TearfulLook = auto()
    ZingZap = auto()
    NaturesMadness = auto()
    MultiAttack = auto()
    TenMVoltThunderbolt = auto()
    MindBlown = auto()
    PlasmaFists = auto()
    PhotonGeyser = auto()
    LightThatBurnstheSky = auto()
    SearingSunrazeSmash = auto()
    MenacingMoonrazeMaelstrom = auto()
    LetsSnuggleForever = auto()
    SplinteredStormshards = auto()
    ClangorousSoulblaze = auto()
    ZippyZap = auto()
    SplishySplash = auto()
    FloatyFall = auto()
    PikaPapow = auto()
    BouncyBubble = auto()
    BuzzyBuzz = auto()
    SizzlySlide = auto()
    GlitzyGlow = auto()
    BaddyBad = auto()
    SappySeed = auto()
    FreezyFrost = auto()
    SparklySwirl = auto()
    VeeveeVolley = auto()
    DoubleIronBash = auto()
    MaxGuard = auto()
    DynamaxCannon = auto()
    SnipeShot = auto()
    JawLock = auto()
    StuffCheeks = auto()
    NoRetreat = auto()
    TarShot = auto()
    MagicPowder = auto()
    DragonDarts = auto()
    Teatime = auto()
    Octolock = auto()
    BoltBeak = auto()
    FishiousRend = auto()
    CourtChange = auto()
    MaxFlare = auto()
    MaxFlutterby = auto()
    MaxLightning = auto()
    MaxStrike = auto()
    MaxKnuckle = auto()
    MaxPhantasm = auto()
    MaxHailstorm = auto()
    MaxOoze = auto()
    MaxGeyser = auto()
    MaxAirstream = auto()
    MaxStarfall = auto()
    MaxWyrmwind = auto()
    MaxMindstorm = auto()
    MaxRockfall = auto()
    MaxQuake = auto()
    MaxDarkness = auto()
    MaxOvergrowth = auto()
    MaxSteelspike = auto()
    ClangorousSoul = auto()
    BodyPress = auto()
    Decorate = auto()
    DrumBeating = auto()
    SnapTrap = auto()
    PyroBall = auto()
    BehemothBlade = auto()
    BehemothBash = auto()
    AuraWheel = auto()
    BreakingSwipe = auto()
    BranchPoke = auto()
    Overdrive = auto()
    AppleAcid = auto()
    GravApple = auto()
    SpiritBreak = auto()
    StrangeSteam = auto()
    LifeDew = auto()
    Obstruct = auto()
    FalseSurrender = auto()
    MeteorAssault = auto()
    Eternabeam = auto()
    SteelBeam = auto()
    ExpandingForce = auto()
    SteelRoller = auto()
    ScaleShot = auto()
    MeteorBeam = auto()
    ShellSideArm = auto()
    MistyExplosion = auto()
    GrassyGlide = auto()
    RisingVoltage = auto()
    TerrainPulse = auto()
    SkitterSmack = auto()
    BurningJealousy = auto()
    LashOut = auto()
    Poltergeist = auto()
    CorrosiveGas = auto()
    Coaching = auto()
    FlipTurn = auto()
    TripleAxel = auto()
    DualWingbeat = auto()
    ScorchingSands = auto()
    JungleHealing = auto()
    WickedBlow = auto()
    SurgingStrikes = auto()
    ThunderCage = auto()
    DragonEnergy = auto()
    FreezingGlare = auto()
    FieryWrath = auto()
    ThunderousKick = auto()
    GlacialLance = auto()
    AstralBarrage = auto()
    EerieSpell = auto()

# status effects, they get cured by lum berry for definition?
class Status_List(IntEnum):
    non = 0
    brn = auto()
    par = auto()
    frz = auto()
    psn = auto()
    tox = auto()
    slp = auto()
    
# Field effects are things that affect both sides
# This is the first and second block in the field of the damage calc
# Missing ones cannot exist in OU
class Terrain_List(IntEnum):
    NoTerrain = 0
    ElectricTerrain = auto()
    GrassyTerrain = auto()
    MistyTerrain = auto()
    PsychicTerrain = auto()

class Weather_List(IntEnum):
    NoWeather = 0
    SunnyDay = auto()
    RainDance = auto()
    Sandstorm = auto()
    Hail = auto()
    
# Side effects are things that are only found on one side
# This is the third block on the damage calc
# Missing ones cannot be in OU
class Hazards_List(IntFlag):
    NoHazards = 0
    StealthRock = auto()
    Spikes = auto()
    Spikes2 = auto()
    Spikes3 = auto()
    ToxicSpikes = auto()
    ToxicSpikes2 = auto()
    Reflect = auto()
    LightScreen = auto()
    Protect = auto()
    LeechSeed = auto()
    Foresight = auto()
    Tailwind = auto()
    AuroraVeil = auto()
    Battery = auto()
    StickyWeb = auto()
    Safeguard = auto()

# see Move dscription
class Ability_List(IntEnum):
    Unknown = 0
    Stench = auto()
    Drizzle = auto()
    SpeedBoost = auto()
    BattleArmor = auto()
    Sturdy = auto()
    Damp = auto()
    Limber = auto()
    SandVeil = auto()
    Static = auto()
    VoltAbsorb = auto()
    WaterAbsorb = auto()
    Oblivious = auto()
    CloudNine = auto()
    CompoundEyes = auto()
    Insomnia = auto()
    ColorChange = auto()
    Immunity = auto()
    FlashFire = auto()
    ShieldDust = auto()
    OwnTempo = auto()
    SuctionCups = auto()
    Intimidate = auto()
    ShadowTag = auto()
    RoughSkin = auto()
    WonderGuard = auto()
    Levitate = auto()
    EffectSpore = auto()
    Synchronize = auto()
    ClearBody = auto()
    NaturalCure = auto()
    LightningRod = auto()
    SereneGrace = auto()
    SwiftSwim = auto()
    Chlorophyll = auto()
    Illuminate = auto()
    Trace = auto()
    HugePower = auto()
    PoisonPoint = auto()
    InnerFocus = auto()
    MagmaArmor = auto()
    WaterVeil = auto()
    MagnetPull = auto()
    Soundproof = auto()
    RainDish = auto()
    SandStream = auto()
    Pressure = auto()
    ThickFat = auto()
    EarlyBird = auto()
    FlameBody = auto()
    RunAway = auto()
    KeenEye = auto()
    HyperCutter = auto()
    Pickup = auto()
    Truant = auto()
    Hustle = auto()
    CuteCharm = auto()
    Plus = auto()
    Minus = auto()
    Forecast = auto()
    StickyHold = auto()
    ShedSkin = auto()
    Guts = auto()
    MarvelScale = auto()
    LiquidOoze = auto()
    Overgrow = auto()
    Blaze = auto()
    Torrent = auto()
    Swarm = auto()
    RockHead = auto()
    Drought = auto()
    ArenaTrap = auto()
    VitalSpirit = auto()
    WhiteSmoke = auto()
    PurePower = auto()
    ShellArmor = auto()
    AirLock = auto()
    TangledFeet = auto()
    MotorDrive = auto()
    Rivalry = auto()
    Steadfast = auto()
    SnowCloak = auto()
    Gluttony = auto()
    AngerPoint = auto()
    Unburden = auto()
    Heatproof = auto()
    Simple = auto()
    DrySkin = auto()
    Download = auto()
    IronFist = auto()
    PoisonHeal = auto()
    Adaptability = auto()
    SkillLink = auto()
    Hydration = auto()
    SolarPower = auto()
    QuickFeet = auto()
    Normalize = auto()
    Sniper = auto()
    MagicGuard = auto()
    NoGuard = auto()
    Stall = auto()
    Technician = auto()
    LeafGuard = auto()
    Klutz = auto()
    MoldBreaker = auto()
    SuperLuck = auto()
    Aftermath = auto()
    Anticipation = auto()
    Forewarn = auto()
    Unaware = auto()
    TintedLens = auto()
    Filter = auto()
    SlowStart = auto()
    Scrappy = auto()
    StormDrain = auto()
    IceBody = auto()
    SolidRock = auto()
    SnowWarning = auto()
    HoneyGather = auto()
    Frisk = auto()
    Reckless = auto()
    Multitype = auto()
    FlowerGift = auto()
    BadDreams = auto()
    Pickpocket = auto()
    SheerForce = auto()
    Contrary = auto()
    Unnerve = auto()
    Defiant = auto()
    Defeatist = auto()
    CursedBody = auto()
    Healer = auto()
    FriendGuard = auto()
    WeakArmor = auto()
    HeavyMetal = auto()
    LightMetal = auto()
    Multiscale = auto()
    ToxicBoost = auto()
    FlareBoost = auto()
    Harvest = auto()
    Telepathy = auto()
    Moody = auto()
    Overcoat = auto()
    PoisonTouch = auto()
    Regenerator = auto()
    BigPecks = auto()
    SandRush = auto()
    WonderSkin = auto()
    Analytic = auto()
    Illusion = auto()
    Imposter = auto()
    Infiltrator = auto()
    Mummy = auto()
    Moxie = auto()
    Justified = auto()
    Rattled = auto()
    MagicBounce = auto()
    SapSipper = auto()
    Prankster = auto()
    SandForce = auto()
    IronBarbs = auto()
    ZenMode = auto()
    VictoryStar = auto()
    Turboblaze = auto()
    Teravolt = auto()
    AromaVeil = auto()
    FlowerVeil = auto()
    CheekPouch = auto()
    Protean = auto()
    FurCoat = auto()
    Magician = auto()
    Bulletproof = auto()
    Competitive = auto()
    StrongJaw = auto()
    Refrigerate = auto()
    SweetVeil = auto()
    StanceChange = auto()
    GaleWings = auto()
    MegaLauncher = auto()
    GrassPelt = auto()
    Symbiosis = auto()
    ToughClaws = auto()
    Pixilate = auto()
    Gooey = auto()
    Aerilate = auto()
    ParentalBond = auto()
    DarkAura = auto()
    FairyAura = auto()
    AuraBreak = auto()
    PrimordialSea = auto()
    DesolateLand = auto()
    DeltaStream = auto()
    Stamina = auto()
    WimpOut = auto()
    EmergencyExit = auto()
    WaterCompaction = auto()
    Merciless = auto()
    ShieldsDown = auto()
    Stakeout = auto()
    WaterBubble = auto()
    Steelworker = auto()
    Berserk = auto()
    SlushRush = auto()
    LongReach = auto()
    LiquidVoice = auto()
    Triage = auto()
    Galvanize = auto()
    SurgeSurfer = auto()
    Schooling = auto()
    Disguise = auto()
    BattleBond = auto()
    PowerConstruct = auto()
    Corrosion = auto()
    Comatose = auto()
    QueenlyMajesty = auto()
    InnardsOut = auto()
    Dancer = auto()
    Battery = auto()
    Fluffy = auto()
    Dazzling = auto()
    SoulHeart = auto()
    TanglingHair = auto()
    Receiver = auto()
    PowerofAlchemy = auto()
    BeastBoost = auto()
    RKSSystem = auto()
    ElectricSurge = auto()
    PsychicSurge = auto()
    MistySurge = auto()
    GrassySurge = auto()
    FullMetalBody = auto()
    ShadowShield = auto()
    PrismArmor = auto()
    Neuroforce = auto()
    IntrepidSword = auto()
    DauntlessShield = auto()
    Libero = auto()
    BallFetch = auto()
    CottonDown = auto()
    PropellerTail = auto()
    MirrorArmor = auto()
    GulpMissile = auto()
    Stalwart = auto()
    SteamEngine = auto()
    PunkRock = auto()
    SandSpit = auto()
    IceScales = auto()
    Ripen = auto()
    IceFace = auto()
    PowerSpot = auto()
    Mimicry = auto()
    ScreenCleaner = auto()
    SteelySpirit = auto()
    PerishBody = auto()
    WanderingSpirit = auto()
    GorillaTactics = auto()
    NeutralizingGas = auto()
    PastelVeil = auto()
    HungerSwitch = auto()
    QuickDraw = auto()
    UnseenFist = auto()
    CuriousMedicine = auto()
    Transistor = auto()
    DragonsMaw = auto()
    ChillingNeigh = auto()
    GrimNeigh = auto()
    AsOneI = auto()
    AsOneG = auto()

if (__name__ == "__main__"):
    for path, dirs, files in os.walk("scrape/"):
        for filename in files:
            full = os.path.join(path, filename)
            csv = "scrape-out/" + filename[:-5] # removes '.json'
            try:
                Replay(full, csv)
            except:
                print(" Error at this file")
                traceback.print_exc()
                pass